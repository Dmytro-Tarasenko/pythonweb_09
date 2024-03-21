"""Scrapy scraper for and parser for the website https://quotes.toscrape.com/"""
from typing import Any

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response


class QuoteSpider(scrapy.Spider):
    """Quotes Spider with xpath"""
    name = "quotes"

    allowed_domains = [
        "quotes.toscrape.com"
    ]

    start_urls = [
        "https://quotes.toscrape.com"
    ]
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEEDS": {
            "quotes.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4
            }
        }
    }

    def parse(self, response: Response, **kwargs) -> Any:
        for quote_div in response.xpath("/html//div[@class='quote']"):
            author = quote_div.xpath("span/small[@class='author']/text()").get().strip()
            quote = quote_div.xpath("span[@class='text']/text()").get().strip()
            tags = quote_div.xpath("div/meta[@class='keywords']/@content").get().split(",")
            yield {
                "author": author,
                "quote": quote,
                "tags": tags
            }

        next_page = response.xpath("//li[@class='next']/a/@href").get()
        if next_page:
            yield scrapy.Request(url=self.start_urls[0] + next_page)


class AuthorSpider(scrapy.Spider):
    """Author Spider with css"""
    name = "authors"
    allowed_domains = [
        "quotes.toscrape.com"
    ]

    start_urls = [
        "https://quotes.toscrape.com/"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "FEED_EXPORT_ENCODING": "utf-8",
        "FEEDS": {
            "authors.json": {
                "format": "json",
                "encoding": "utf-8",
                "indent": 4
            }
        }
    }

    def parse(self, response: Response, **kwargs) -> Any:
        author_page_links = response.css(".author + a")
        yield from response.follow_all(author_page_links, self.parse_author)

        pagination_links = response.css("li.next a")
        yield from response.follow_all(pagination_links, self.parse)

    @staticmethod
    def parse_author(response):
        def extract_with_css(query):
            return response.css(query).get(default="").strip()

        yield {
            "fullname": extract_with_css("h3.author-title::text"),
            "born_date": extract_with_css(".author-born-date::text"),
            "description": extract_with_css(".author-description::text"),
            "born_location": extract_with_css(".author-born-date::text")
        }


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(AuthorSpider)
    process.crawl(QuoteSpider)
    process.start()
