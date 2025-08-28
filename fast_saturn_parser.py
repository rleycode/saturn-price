#!/usr/bin/env python3

import os
import sys
import time
import requests
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from bs4 import BeautifulSoup
import threading
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ProductPrice:
    sku: str
    name: str
    price: float
    availability: str
    url: str
    old_price: Optional[float] = None

class FastSaturnParser:
    
    def __init__(self, max_workers: int = 10, request_delay: float = 0.1):
        self.base_url = "https://nnv.saturn.net"
        self.search_url = f"{self.base_url}/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s="
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.log_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def parse_single_product(self, sku: str) -> Optional[ProductPrice]:
        try:
            url = f"{self.search_url}{sku}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            product_items = soup.find_all('div', class_='catalog-item')
            
            for item in product_items:
                article_elem = item.find('span', class_='article')
                if not article_elem:
                    continue
                
                article_text = article_elem.get_text(strip=True)
                if sku not in article_text:
                    continue
                
                name_elem = item.find('a', class_='name')
                name = name_elem.get_text(strip=True) if name_elem else f"Товар {sku}"
                
                price_elem = item.find('span', {'data-price': True})
                if not price_elem:
                    continue
                
                try:
                    price = float(price_elem['data-price'])
                except (ValueError, KeyError):
                    continue
                
                availability = "В наличии"
                if item.find('span', class_='not-available'):
                    availability = "Нет в наличии"
                
                return ProductPrice(
                    sku=sku,
                    name=name,
                    price=price,
                    availability=availability,
                    url=url
                )
            
            return None
            
        except requests.exceptions.RequestException as e:
            with self.log_lock:
                self.logger.warning(f"Ошибка запроса для {sku}: {e}")
            return None
        except Exception as e:
            with self.log_lock:
                self.logger.error(f"Ошибка парсинга {sku}: {e}")
            return None
    
    def parse_products_batch(self, skus: List[str], output_file: str = None) -> List[ProductPrice]:
        start_time = time.time()
        results = []
        
        self.logger.info(f"Начинаем быстрый парсинг {len(skus)} товаров ({self.max_workers} потоков)")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_sku = {
                executor.submit(self.parse_single_product, sku): sku 
                for sku in skus
            }
            
            for future in as_completed(future_to_sku):
                sku = future_to_sku[future]
                self.processed_count += 1
                
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.success_count += 1
                        
                        with self.log_lock:
                            self.logger.info(f"Найден {sku}: {result.price} руб.")
                    else:
                        self.error_count += 1
                        with self.log_lock:
                            self.logger.warning(f"Не найден {sku}")
                    
                    if self.processed_count % 50 == 0:
                        progress = (self.processed_count / len(skus)) * 100
                        elapsed = time.time() - start_time
                        rate = self.processed_count / elapsed if elapsed > 0 else 0
                        
                        with self.log_lock:
                            self.logger.info(f"Прогресс: {self.processed_count}/{len(skus)} ({progress:.1f}%) - {rate:.1f} товаров/сек")
                
                except Exception as e:
                    self.error_count += 1
                    with self.log_lock:
                        self.logger.error(f"Ошибка обработки {sku}: {e}")
                
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
        
        if output_file and results:
            self.save_results(results, output_file)
        
        elapsed = time.time() - start_time
        rate = len(skus) / elapsed if elapsed > 0 else 0
        
        self.logger.info(f"Парсинг завершен за {elapsed:.1f}с")
        self.logger.info(f"Скорость: {rate:.1f} товаров/сек")
        self.logger.info(f"Найдено: {self.success_count}/{len(skus)} товаров")
        
        return results
    
    def save_results(self, results: List[ProductPrice], output_file: str):
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['sku', 'name', 'price', 'availability', 'url'])
            
            for result in results:
                writer.writerow([
                    result.sku,
                    result.name,
                    result.price,
                    result.availability,
                    result.url
                ])
        
        self.logger.info(f"Результаты сохранены: {output_file}")


def load_skus_from_file(file_path: str) -> List[str]:
    skus = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            sku = line.strip()
            if sku:
                skus.append(sku)
    return skus


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fast Saturn Parser')
    parser.add_argument('--skus-file', help='Файл с артикулами')
    parser.add_argument('--output', default='output/saturn_fast_prices.csv', help='Выходной файл')
    parser.add_argument('--workers', type=int, default=10, help='Количество потоков')
    parser.add_argument('--delay', type=float, default=0.1, help='Задержка между запросами (сек)')
    parser.add_argument('--batch-size', type=int, help='Ограничить количество товаров')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    if args.skus_file:
        skus = load_skus_from_file(args.skus_file)
    else:
        sys.path.append('.')
        from bitrix_integration import BitrixClient, BitrixConfig
        
        config = BitrixConfig(
            mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
            mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
            mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
            mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
            mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
            iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
            supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
        )
        
        with BitrixClient(config) as bitrix:
            products = bitrix.get_products_by_prefix()
            skus = [p.article.replace(config.supplier_prefix, '') for p in products]
    
    if not skus:
        print("Нет артикулов для парсинга")
        return 1
    
    if args.batch_size:
        skus = skus[:args.batch_size]
    
    parser = FastSaturnParser(max_workers=args.workers, request_delay=args.delay)
    results = parser.parse_products_batch(skus, args.output)
    
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
