"""Scrapy scraper for and parser for the website https://quotes.toscrape.com/"""
import json
import requests

from models import AuthorJsonModel, QuoteJsonModel
