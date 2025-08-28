#!/usr/bin/env python3

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
from bs4 import BeautifulSoup

def setup_logging():
    logger = logging.getLogger(__name__)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    handler = RotatingFileHandler(
        log_dir / "saturn_parser.log",
        maxBytes=10*1024*1024,
        backupCount=1
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()


@dataclass
class ProductPrice:
    sku: str
    name: str
    price: float
    old_price: Optional[float]
    availability: str
    url: str
    parsed_at: datetime


class ProcessLock:
    
    def __init__(self, lock_file: str):
        self.lock_file = Path(lock_file)
        self.acquired = False
    
    def __enter__(self):
        if self.lock_file.exists():
            try:
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                
                try:
                    os.kill(pid, 0)
                    raise RuntimeError(f"Процесс уже запущен (PID: {pid})")
                except OSError:
                    self.lock_file.unlink()
            except (ValueError, FileNotFoundError):
                self.lock_file.unlink()
        
        with open(self.lock_file, 'w') as f:
            f.write(str(os.getpid()))
        
        self.acquired = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired and self.lock_file.exists():
            self.lock_file.unlink()


class SaturnParser:
    
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
        
        self.request_delay = 1.0
        self.max_retries = 3
        self.timeout = 30
        
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
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
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
        for pattern in self.name_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            if matches:
                name = matches[0].strip()
                name = re.sub(r'\s+', ' ', name)
                if len(name) > 5:
                    return name
        return None
    
    def _search_product_data(self, sku: str) -> Optional[dict]:
        search_queries = [
            f"тов-{sku}",            sku,
            sku.replace('-', ''),
            sku.replace('_', ''),
            sku.upper(),
            sku.lower()
        ]
        
        for query in search_queries:
            search_url = f"{self.base_url}/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={query}"
            response = self._make_request(search_url)
            
            if not response:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            page_text = soup.get_text()
            
            if "найдено:" in page_text.lower() and "товар" in page_text.lower():
                logger.info(f"Найдена страница результатов поиска для {sku}")
                
                product_links = soup.find_all('a', href=re.compile(r'/catalog/[^/]+/[^/]+/$'))
                
                for link in product_links:
                    link_text = link.get_text(strip=True).lower()
                    href = link.get('href')
                    
                    if (sku in link_text or 
                        f"тов-{sku}" in link_text or
                        any(keyword in link_text for keyword in ["брусок", "строганый", "сухой"])):
                        
                        if not href.startswith('http'):
                            product_url = urljoin(self.base_url, href)
                        else:
                            product_url = href
                        
                        logger.info(f"Найдена ссылка на товар: {product_url}")
                        
                        product_response = self._make_request(product_url)
                        if not product_response:
                            continue
                        
                        product_soup = BeautifulSoup(product_response.text, 'html.parser')
                        
                        price_elements = product_soup.find_all(attrs={'data-price': True})
                        
                        if price_elements:
                            try:
                                price_value = price_elements[0].get('data-price')
                                price = float(price_value)
                                
                                name = None
                                
                                for tag in ['h1', 'h2', 'title']:
                                    title_elem = product_soup.find(tag)
                                    if title_elem:
                                        name = title_elem.get_text(strip=True)
                                        if len(name) > 10:
                                            break
                                
                                if not name:
                                    name = link.get_text(strip=True)
                                
                                logger.info(f"Найден товар {sku}: {name} - {price}₽")
                                
                                return ProductPrice(
                                    sku=sku,
                                    name=name,
                                    price=price,
                                    old_price=None,
                                    url=product_url,
                                    timestamp=datetime.now()
                                )
                                
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Ошибка парсинга цены для {sku}: {e}")
                                continue
            
            sku_with_prefix = f"тов-{sku}"
            elements_with_sku = soup.find_all(string=re.compile(re.escape(sku_with_prefix)))
            
            if not elements_with_sku:
                elements_with_sku = soup.find_all(string=re.compile(re.escape(sku)))
            
            for sku_element in elements_with_sku:
                current = sku_element.parent
                for _ in range(10):
                    if not current:
                        break
                    
                    price_elements = current.find_all(attrs={'data-price': True})
                    if price_elements:
                        try:
                            price_value = price_elements[0].get('data-price')
                            price = float(price_value)
                            
                            text_content = current.get_text()
                            sku_pos = text_content.find(sku_with_prefix)
                            if sku_pos == -1:
                                sku_pos = text_content.find(sku)
                            
                            name = None
                            
                            if sku_pos != -1:
                                start = max(0, sku_pos - 100)
                                end = min(len(text_content), sku_pos + 200)
                                context = text_content[start:end]
                                
                                lines = context.split('\n')
                                for line in lines:
                                    line = line.strip()
                                    if len(line) > 10 and sku not in line and 'руб' not in line.lower():
                                        if any(word in line.lower() for word in ['брусок', 'доска', 'рейка', 'балка']):
                                            name = line
                                            break
                            
                            if not name:
                                name = f"Товар {sku}"
                            
                            return {
                                'name': name,
                                'price': price,
                                'availability': 'Да',
                                'url': search_url
                            }
                            
                        except (ValueError, TypeError):
                            continue
                    
                    current = current.parent
        
        return None
    
    def parse_product(self, sku: str) -> Optional[ProductPrice]:
        logger.info(f"Парсинг товара: {sku}")
        
        product_data = self._search_product_data(sku)
        if not product_data:
            logger.warning(f"Товар не найден: {sku}")
            return None
        
        return ProductPrice(
            sku=sku,
            name=product_data['name'],
            price=product_data['price'],
            old_price=None,
            availability=product_data['availability'],
            url=product_data['url'],
            parsed_at=datetime.now()
        )
    
    def parse_products(self, skus: List[str], output_file: str = None) -> List[ProductPrice]:
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
        
        if output_file:
            self.save_results(results, output_file)
        
        logger.info(f"Парсинг завершен. Обработано: {len(results)}/{total}")
        return results
    
    def save_results(self, results: List[ProductPrice], output_file: str):
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
    skus = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            sku = line.strip()
            if sku and not sku.startswith('#'):
                skus.append(sku)
    return skus


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Saturn Price Parser')
    parser.add_argument('--skus', help='Файл с артикулами')
    parser.add_argument('--sku', help='Один артикул для парсинга')
    parser.add_argument('--output', default='output/saturn_prices.csv', help='Выходной файл')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета')
    
    args = parser.parse_args()
    
    with ProcessLock('/tmp/saturn_parser.lock'):
        saturn_parser = SaturnParser()
        
        if args.sku:
            skus = [args.sku]
        elif args.skus:
            skus = load_skus_from_file(args.skus)
        else:
            logger.error("Укажите --sku или --skus")
            return 1
        
        if len(skus) > args.batch_size:
            logger.info(f"Ограничиваем до {args.batch_size} товаров")
            skus = skus[:args.batch_size]
        
        start_time = time.time()
        results = saturn_parser.parse_products(skus, args.output)
        elapsed = time.time() - start_time
        
        logger.info(f"Время выполнения: {elapsed:.1f}с")
        logger.info(f"Скорость: {len(results)/elapsed:.1f} товаров/с")
        
        return 0


if __name__ == '__main__':
    sys.exit(main())
