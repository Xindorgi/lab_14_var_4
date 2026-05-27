import os
from dataclasses import dataclass
from typing import List

@dataclass
class RSSSource:
    url: str
    name: str
    type: str  # 'rss' or 'html'

# Пример RSS-лент для тестирования
RSS_SOURCES: List[RSSSource] = [
    RSSSource(
        url="https://lenta.ru/rss/news",
        name="Lenta.ru News",
        type="rss"
    ),
    RSSSource(
        url="https://www.interfax.ru/rss.asp",
        name="Interfax",
        type="rss"
    ),
    RSSSource(
        url="https://ria.ru/export/rss2/index.xml",
        name="RIA Novosti",
        type="rss"
    ),
    RSSSource(
        url="https://www.bbc.com/russian/news",
        name="BBC Russian",
        type="html"  # Для демонстрации HTML парсинга
    )
]

# Настройки парсера
PARSER_CONFIG = {
    "max_concurrent_requests": 10,
    "request_timeout": 30,
    "user_agent": "NewsScraper/1.0 (Python aiohttp)",
    "output_dir": "data",
    "output_filename": "news_data.json"
}

# Настройки логирования
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "scraper.log"
}