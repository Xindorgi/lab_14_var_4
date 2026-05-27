#!/usr/bin/env python3
"""
Асинхронный парсер новостных сайтов для RSS и HTML источников.
Сохраняет данные в локальный JSON файл.
"""

import asyncio
import aiohttp
import aiofiles
import feedparser
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
import ujson

from config import RSS_SOURCES, PARSER_CONFIG, LOG_CONFIG

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"]
)
logger = logging.getLogger(__name__)

class AsyncNewsScraper:
    """Асинхронный сборщик новостей из RSS и HTML источников."""
    
    def __init__(self):
        self.session = None
        self.semaphore = asyncio.Semaphore(PARSER_CONFIG["max_concurrent_requests"])
        self.output_file = f"{PARSER_CONFIG['output_dir']}/{PARSER_CONFIG['output_filename']}"
        
    async def __aenter__(self):
        """Контекстный менеджер для инициализации сессии."""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": PARSER_CONFIG["user_agent"]},
            timeout=aiohttp.ClientTimeout(total=PARSER_CONFIG["request_timeout"])
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе."""
        if self.session:
            await self.session.close()
    
    async def fetch_url(self, url: str) -> str:
        """Асинхронное получение содержимого по URL."""
        async with self.semaphore:
            try:
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    return await response.text()
            except Exception as e:
                logger.error(f"Ошибка при запросе {url}: {e}")
                return ""
    
    async def parse_rss(self, source) -> List[Dict[str, Any]]:
        """Парсинг RSS ленты."""
        logger.info(f"Парсинг RSS: {source.name}")
        
        content = await self.fetch_url(source.url)
        if not content:
            return []
        
        # Используем feedparser для парсинга RSS
        feed = feedparser.parse(content)
        articles = []
        
        for entry in feed.entries:
            article = {
                "source": source.name,
                "source_type": "rss",
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "description": entry.get("description", ""),
                "published": entry.get("published", ""),
                "published_parsed": entry.get("published_parsed"),
                "authors": entry.get("authors", []),
                "categories": entry.get("categories", []),
                "scraped_at": datetime.utcnow().isoformat()
            }
            articles.append(article)
        
        logger.info(f"Найдено {len(articles)} статей в {source.name}")
        return articles
    
    async def parse_html(self, source) -> List[Dict[str, Any]]:
        """Парсинг HTML страницы (пример для BBC Russian)."""
        logger.info(f"Парсинг HTML: {source.name}")
        
        content = await self.fetch_url(source.url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        articles = []
        
        # Пример: парсинг заголовков новостей с BBC Russian
        # Это упрощенный пример, реальный парсинг будет зависеть от структуры сайта
        news_items = soup.find_all('article', class_='bbc-1k2rqgq') or soup.find_all('div', class_='gs-c-promo')
        
        for item in news_items[:10]:  # Ограничимся 10 статьями для демонстрации
            title_elem = item.find('h3') or item.find('a', class_='gs-c-promo-heading')
            link_elem = item.find('a', href=True)
            
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                link = link_elem['href']
                
                # Преобразование относительных ссылок в абсолютные
                if link.startswith('/'):
                    link = f"https://www.bbc.com{link}"
                
                article = {
                    "source": source.name,
                    "source_type": "html",
                    "title": title,
                    "link": link,
                    "description": "",
                    "published": "",
                    "scraped_at": datetime.utcnow().isoformat()
                }
                articles.append(article)
        
        logger.info(f"Найдено {len(articles)} статей в {source.name} (HTML)")
        return articles
    
    async def scrape_source(self, source) -> List[Dict[str, Any]]:
        """Сбор данных из одного источника."""
        if source.type == "rss":
            return await self.parse_rss(source)
        elif source.type == "html":
            return await self.parse_html(source)
        else:
            logger.warning(f"Неизвестный тип источника: {source.type}")
            return []
    
    async def save_to_json(self, articles: List[Dict[str, Any]]):
        """Сохранение статей в JSON файл."""
        import os
        os.makedirs(PARSER_CONFIG["output_dir"], exist_ok=True)
        
        # Чтение существующих данных, если файл есть
        existing_data = []
        if os.path.exists(self.output_file):
            try:
                async with aiofiles.open(self.output_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    existing_data = ujson.loads(content) if content else []
            except Exception as e:
                logger.error(f"Ошибка при чтении файла {self.output_file}: {e}")
        
        # Добавление новых статей
        existing_data.extend(articles)
        
        # Сохранение обновленных данных
        try:
            async with aiofiles.open(self.output_file, 'w', encoding='utf-8') as f:
                await f.write(ujson.dumps(existing_data, indent=2, ensure_ascii=False))
            logger.info(f"Сохранено {len(articles)} статей в {self.output_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в файл {self.output_file}: {e}")
    
    async def run(self):
        """Основной метод запуска парсера."""
        logger.info("Запуск асинхронного парсера новостей")
        
        all_articles = []
        
        # Параллельный парсинг всех источников
        tasks = [self.scrape_source(source) for source in RSS_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при парсинге источника {RSS_SOURCES[i].name}: {result}")
            elif result:
                all_articles.extend(result)
        
        # Сохранение результатов
        if all_articles:
            await self.save_to_json(all_articles)
            logger.info(f"Всего собрано {len(all_articles)} статей")
        else:
            logger.warning("Не удалось собрать ни одной статьи")

async def main():
    """Точка входа в приложение."""
    async with AsyncNewsScraper() as scraper:
        await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())