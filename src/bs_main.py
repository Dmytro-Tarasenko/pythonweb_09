"""BS4 scrapper and parser for the website https://quotes.toscrape.com/"""
import json
from typing import Optional, Dict

import requests
from threading import Thread, Lock, Semaphore
import logging
from bs4 import BeautifulSoup

from models import QuoteJsonModel, AuthorJsonModel

AUTHORS = {}
QUOTES = []

logging.basicConfig(level=logging.INFO,
                    format="%(threadName)s %(asctime)s: %(message)s")
logger = logging.getLogger("bs4_scrapper")
base_url = "https://quotes.toscrape.com"


def quotes_from_page(pool: Semaphore,
                     target: str = "",
                     locks: Optional[Dict[str, Lock]] = None) -> None:
    """Scrap, parse target page and write parsed quotes
     as QuoteJsonModel to QUOTES list
        params:
            target(str) - url for target page
            quote_lock(Lock) - Lock object for QUOTES synchronization

        return:
            None
    """
    global QUOTES
    childs = []

    target = base_url + target
    logger.info(f"scrapping started with target {target}")
    page = requests.get(target)
    soup = BeautifulSoup(page.text, 'lxml')
    if next_tag := soup.select("li.next a"):
        next_ = next_tag[0].get("href")
        with pool:
            quote_thread = Thread(target=quotes_from_page,
                                  kwargs={"locks": lock_pool,
                                          "pool": scrapers_pool,
                                          "target": next_})
            childs.append(quote_thread)
            quote_thread.start()

    if quote_divs := soup.select("div.quote"):
        for div in quote_divs:
            quote_text = div.select_one("span.text").text
            tags_list = div.select_one("meta.keywords").get("content").split(",")
            small_author = div.select_one("small.author")
            author_name = small_author.text
            author_href = small_author.find_next_sibling("a").get("href")

            quote_model = QuoteJsonModel(quote=quote_text,
                                         author=author_name,
                                         tags=tags_list)
            locks['quotes'].acquire()
            QUOTES.append(quote_model)
            locks['quotes'].release()
            
            with pool:
                author_thread = Thread(target=author_from_quote,
                                       kwargs={"target": author_href,
                                               "name": author_name,
                                               "locks": locks})
                childs.append(author_thread)
                author_thread.start()

    [child.join() for child in childs]


def author_from_quote(target: str,
                      name: str,
                      locks: Dict[str, Lock]) -> None:
    global AUTHORS
    logger.info(f"Author scrapping started for {target}")
    if _ := AUTHORS.setdefault(name, None):
        logger.info(f"Author {name} has already been processed.")
        return
    target = base_url + target
    author_page = requests.get(target)
    soup = BeautifulSoup(author_page.text, "lxml")

    born_date = soup.select_one("span.author-born-date").text
    born_place = soup.select_one("span.author-born-location").text
    bio = soup.select_one("div.author-description").text
    bio = bio.replace("\n", "").strip()

    author_model = AuthorJsonModel(fullname=name,
                                   born_date=born_date,
                                   born_location=born_place,
                                   description=bio)
    locks['authors'].acquire()
    AUTHORS[name] = author_model
    locks['authors'].release()


if __name__ == "__main__":
    scrapers_pool = Semaphore(10)
    quotes_lock = Lock()
    authors_lock = Lock()
    lock_pool = {"quotes": quotes_lock,
                 "authors": authors_lock}

    logger.info("Scrapping started!")
    starter = Thread(target=quotes_from_page,
                     kwargs={"locks": lock_pool,
                             "pool": scrapers_pool})
    starter.start()
    starter.join()
    logger.info("Workers`ve done their jobs!")

    json_authors = list(author.model_dump(warnings=False)
                        for author in AUTHORS.values())
    with open("authors.json", "w", encoding="utf-8") as fout:
        json.dump(json_authors, fout,
                  ensure_ascii=False, default=str,
                  indent=4)

    json_quotes = [quote.model_dump(warnings=False)
                   for quote in QUOTES]

    with open("quotes.json", "w", encoding="utf-8") as fout:
        json.dump(json_quotes, fout,
                  ensure_ascii=False, default=str,
                  indent=4)
