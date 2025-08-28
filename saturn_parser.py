#!/usr/bin/env python3
"""
Saturn Price Parser - Автономный парсер цен с сайта Saturn
"""

import os
import sys
import time
import json
import csv
import requests
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, quote_plus
import logging
from logging.handlers import RotatingFileHandler

# Настройка логирования
def setup_logging():
    """Настройка логирования с ротацией файлов"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Ротация логов (максимум 2 файла по 10MB)
    handler = RotatingFileHandler(
        log_dir / "saturn_parser.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=1
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Консольный вывод
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()


@dataclass
class ProductPrice:
    """Цена товара с Saturn"""
    sku: str
    name: str
    price: float
    old_price: Optional[float]
    availability: str
    url: str
    parsed_at: datetime


class ProcessLock:
    """Блокировка процесса для предотвращения одновременных запусков"""
    
    def __init__(self, lock_file: str):
        self.lock_file = Path(lock_file)
        self.acquired = False
    
    def __enter__(self):
        if self.lock_file.exists():
            # Проверяем, не завис ли процесс
            try:
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Проверяем, существует ли процесс (Linux/Unix)
                try:
                    os.kill(pid, 0)
                    raise RuntimeError(f"Процесс уже запущен (PID: {pid})")
                except OSError:
                    # Процесс не существует, удаляем старый lock
                    self.lock_file.unlink()
            except (ValueError, FileNotFoundError):
                self.lock_file.unlink()
        
        # Создаем новый lock
        with open(self.lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        self.acquired = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired and self.lock_file.exists():
            self.lock_file.unlink()


class SaturnParser:
    """Парсер цен с сайта Saturn"""
    
    def __init__(self):
        self.base_url = "https://nnv.saturn.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Настройки парсинга
        self.request_delay = 1.0  # Задержка между запросами
        self.max_retries = 3
        self.timeout = 30
        
        # Регулярные выражения для парсинга
        self.price_patterns = [
            r'<span[^>]*class="[^"]*price[^"]*"[^>]*>([0-9\s,\.]+)',
            r'"price":\s*"?([0-9\s,\.]+)"?',
            r'data-price="([0-9\s,\.]+)"',
            r'<meta[^>]*property="product:price:amount"[^>]*content="([0-9\s,\.]+)"',
        ]
        
        self.name_patterns = [
            r'<h1[^>]*>([^<]+)</h1>',
            r'<title>([^<]+)</title>',
            r'"name":\s*"([^"]+)"',
            r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
        ]
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Безопасный HTTP запрос с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Слишком много запросов - увеличиваем задержку
                    wait_time = (attempt + 1) * 5
                    logger.warning(f"Rate limit hit, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep((attempt + 1) * 2)
        
        return None
    
    def _extract_price(self, html: str) -> Optional[float]:
        """Извлечение цены из HTML"""
        for pattern in self.price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                price_str = matches[0].replace(' ', '').replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None
    
    def _extract_name(self, html: str) -> Optional[str]:
        """Извлечение названия товара из HTML"""
        for pattern in self.name_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                name = matches[0].strip()
                # Очистка названия от лишних символов
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 5:  # Минимальная длина названия
                    return name
        return None
    
    def _search_product_url(self, sku: str) -> Optional[str]:
        """Поиск URL товара по артикулу"""
        search_queries = [
            sku,
            sku.replace('-', ''),
            sku.replace('_', ''),
            sku.upper(),
            sku.lower()
        ]
        
        for query in search_queries:
            search_url = f"{self.base_url}/search/?q={quote_plus(query)}"
            response = self._make_request(search_url)
            
            if not response:
                continue
            
            # Поиск ссылок на товары в результатах поиска
            product_links = re.findall(
                r'<a[^>]*href="([^"]*(?:product|item|goods)[^"]*)"[^>]*>',
                response.text,
                re.IGNORECASE
            )
            
            for link in product_links:
                if link.startswith('/'):
                    link = urljoin(self.base_url, link)
                
                # Проверяем, что ссылка содержит артикул
                if any(q.lower() in link.lower() for q in [sku, sku.replace('-', '')]):
                    return link
        
        return None
    
    def parse_product(self, sku: str) -> Optional[ProductPrice]:
        """Парсинг товара по артикулу"""
        logger.info(f"Парсинг товара: {sku}")
        
        # Поиск URL товара
        product_url = self._search_product_url(sku)
        if not product_url:
            logger.warning(f"Товар не найден: {sku}")
            return None
        
        # Получение страницы товара
        response = self._make_request(product_url)
        if not response:
            logger.error(f"Не удалось загрузить страницу: {product_url}")
            return None
        
        # Извлечение данных
        name = self._extract_name(response.text)
        price = self._extract_price(response.text)
        
        if not price:
            logger.warning(f"Цена не найдена для {sku}")
            return None
        
        if not name:
            name = f"Товар {sku}"
        
        # Определение доступности
        availability = "Да"
        if any(phrase in response.text.lower() for phrase in ['нет в наличии', 'отсутствует', 'под заказ']):
            availability = "Нет"
        
        # Поиск старой цены (если есть)
        old_price = None
        old_price_patterns = [
            r'<span[^>]*class="[^"]*old[^"]*price[^"]*"[^>]*>([0-9\s,\.]+)',
            r'"old_price":\s*"?([0-9\s,\.]+)"?',
        ]
        
        for pattern in old_price_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                try:
                    old_price = float(matches[0].replace(' ', '').replace(',', '.'))
                    break
                except ValueError:
                    continue
        
        return ProductPrice(
            sku=sku,
            name=name,
            price=price,
            old_price=old_price,
            availability=availability,
            url=product_url,
            parsed_at=datetime.now()
        )
    
    def parse_products(self, skus: List[str], output_file: str = None) -> List[ProductPrice]:
        """Парсинг списка товаров"""
        results = []
        total = len(skus)
        
        logger.info(f"Начинаем парсинг {total} товаров")
        
        for i, sku in enumerate(skus, 1):
            logger.info(f"Прогресс: {i}/{total} ({i/total*100:.1f}%)")
            
            try:
                product = self.parse_product(sku)
                if product:
                    results.append(product)
                    logger.info(f"✅ {sku}: {product.name} - {product.price} руб.")
                else:
                    logger.warning(f"❌ {sku}: не найден")
                    
            except Exception as e:
                logger.error(f"Ошибка парсинга {sku}: {e}")
        
        # Сохранение результатов
        if output_file:
            self.save_results(results, output_file)
        
        logger.info(f"Парсинг завершен. Обработано: {len(results)}/{total}")
        return results
    
    def save_results(self, results: List[ProductPrice], output_file: str):
        """Сохранение результатов в CSV"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['sku', 'name', 'price', 'old_price', 'availability', 'url', 'parsed_at'])
            
            for product in results:
                writer.writerow([
                    product.sku,
                    product.name,
                    product.price,
                    product.old_price or '',
                    product.availability,
                    product.url,
                    product.parsed_at.isoformat()
                ])
        
        logger.info(f"Результаты сохранены: {output_path}")


def load_skus_from_file(file_path: str) -> List[str]:
    """Загрузка артикулов из файла"""
    skus = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            sku = line.strip()
            if sku and not sku.startswith('#'):
                skus.append(sku)
    return skus


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Saturn Price Parser')
    parser.add_argument('--skus', help='Файл с артикулами')
    parser.add_argument('--sku', help='Один артикул для парсинга')
    parser.add_argument('--output', default='output/saturn_prices.csv', help='Выходной файл')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета')
    
    args = parser.parse_args()
    
    # Блокировка одновременных запусков
    with ProcessLock('/tmp/saturn_parser.lock'):
        saturn_parser = SaturnParser()
        
        # Определение списка артикулов
        if args.sku:
            skus = [args.sku]
        elif args.skus:
            skus = load_skus_from_file(args.skus)
        else:
            logger.error("Укажите --sku или --skus")
            return 1
        
        # Ограничение размера пакета
        if len(skus) > args.batch_size:
            logger.info(f"Ограничиваем до {args.batch_size} товаров")
            skus = skus[:args.batch_size]
        
        # Парсинг
        start_time = time.time()
        results = saturn_parser.parse_products(skus, args.output)
        elapsed = time.time() - start_time
        
        logger.info(f"Время выполнения: {elapsed:.1f}с")
        logger.info(f"Скорость: {len(results)/elapsed:.1f} товаров/с")
        
        return 0


if __name__ == '__main__':
    sys.exit(main())
