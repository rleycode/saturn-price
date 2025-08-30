#!/usr/bin/env python3
"""
Парсер Saturn на основе sitemap - доступ ко всем товарам по прямым URL
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import time
import csv
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
from dataclasses import dataclass
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from urllib.parse import urljoin

@dataclass
class ProductInfo:
    sku: str
    name: str
    price: float
    url: str
    availability: str = "В наличии"

class SaturnSitemapParser:
    
    def __init__(self, max_workers: int = 20, request_delay: float = 0.1):
        self.base_url = "https://msk.saturn.net"
        self.sitemap_urls = [
            "https://msk.saturn.net/sitemap.xml",
            "https://msk.saturn.net/sitemaps/msk.sitemap.xml"
        ]
        self.max_workers = max_workers
        self.request_delay = request_delay
        
        # Настраиваем сессию с увеличенным пулом соединений
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        self.session = requests.Session()
        
        # Увеличиваем размер пула соединений
        adapter = HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=Retry(total=3, backoff_factor=0.3)
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        
    def get_product_urls_from_sitemap(self) -> List[str]:
        """Извлекает URL товаров из sitemap"""
        
        all_product_urls = set()
        
        for sitemap_url in self.sitemap_urls:
            try:
                self.logger.info(f"Загружаем sitemap: {sitemap_url}")
                
                response = self.session.get(sitemap_url, timeout=15)
                response.raise_for_status()
                
                # Парсим XML
                root = ET.fromstring(response.content)
                
                # Извлекаем все URL
                urls = []
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        urls.append(loc.text)
                
                # Фильтруем URL товаров (глубокие ссылки в каталоге)
                product_urls = []
                for url in urls:
                    if '/catalog/' in url:
                        # Считаем количество слешей после /catalog/
                        catalog_part = url.split('/catalog/', 1)[1]
                        slash_count = catalog_part.count('/')
                        
                        # Товары обычно имеют структуру /catalog/category/subcategory/product/
                        if slash_count >= 2:
                            product_urls.append(url)
                
                self.logger.info(f"Найдено {len(product_urls)} товаров в {sitemap_url}")
                all_product_urls.update(product_urls)
                
            except Exception as e:
                self.logger.error(f"Ошибка загрузки sitemap {sitemap_url}: {e}")
        
        product_urls_list = list(all_product_urls)
        self.logger.info(f"Всего уникальных товаров: {len(product_urls_list)}")
        
        return product_urls_list
    
    def parse_category_page(self, category_url: str) -> List[ProductInfo]:
        """Парсит страницу категории и извлекает все товары"""
        
        try:
            response = self.session.get(category_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            
            # Ищем контейнеры товаров на странице категории
            product_containers = soup.select('div.h_s_list_categor_item_wrap')
            
            for container in product_containers:
                try:
                    # Извлекаем артикул
                    article_elem = container.select_one('p.h_s_list_categor_item_articul')
                    if not article_elem:
                        continue
                    
                    article_text = article_elem.get_text(strip=True)
                    if 'тов-' not in article_text:
                        continue
                    
                    sku = article_text.replace('тов-', '')
                    
                    # Извлекаем название
                    name_elem = container.select_one('p.h_s_list_categor_item_txt')
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                    else:
                        name = "Товар без названия"
                    
                    # Извлекаем цену
                    price = None
                    price_elem = container.select_one('span.js-price-value[data-price]')
                    
                    if price_elem:
                        # Получаем из атрибута data-price
                        data_price = price_elem.get('data-price')
                        if data_price:
                            try:
                                price = float(data_price)
                            except ValueError:
                                pass
                    
                    # Если не нашли цену через data-price, ищем любой span с data-price
                    if not price:
                        price_spans = container.select('span[data-price]')
                        for span in price_spans:
                            data_price = span.get('data-price')
                            if data_price:
                                try:
                                    price = float(data_price)
                                    break
                                except ValueError:
                                    continue
                    
                    if not price:
                        continue
                    
                    # Проверяем наличие
                    availability = "В наличии"
                    if container.find(string=re.compile(r'нет в наличии|отсутствует|под заказ', re.IGNORECASE)):
                        availability = "Нет в наличии"
                    
                    # URL товара - используем URL категории, так как прямых ссылок нет
                    product_url = category_url
                    
                    products.append(ProductInfo(
                        sku=sku,
                        name=name,
                        price=price,
                        url=product_url,
                        availability=availability
                    ))
                    
                except Exception as e:
                    with self.lock:
                        self.logger.warning(f"Ошибка парсинга товара в контейнере: {e}")
                    continue
            
            return products
            
        except Exception as e:
            with self.lock:
                self.logger.warning(f"Ошибка парсинга категории {category_url}: {e}")
            return []
    
    def parse_products_batch(self, category_urls: List[str], target_skus: Set[str] = None) -> List[ProductInfo]:
        """Парсит товары со страниц категорий из sitemap"""
        
        start_time = time.time()
        all_results = []
        
        # Фильтруем URL если указаны целевые SKU
        if target_skus:
            self.logger.info(f"Ищем {len(target_skus)} конкретных товаров среди {len(category_urls)} категорий")
        else:
            self.logger.info(f"Парсим товары из {len(category_urls)} категорий sitemap")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.parse_category_page, url): url 
                for url in category_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                
                with self.lock:
                    self.processed_count += 1
                
                try:
                    category_results = future.result()
                    
                    if category_results:
                        # Фильтруем по целевым SKU если указаны
                        if target_skus:
                            filtered_results = [r for r in category_results if r.sku in target_skus]
                        else:
                            filtered_results = category_results
                        
                        all_results.extend(filtered_results)
                        
                        with self.lock:
                            self.success_count += len(filtered_results)
                            
                            # Логируем найденные товары
                            for result in filtered_results:
                                self.logger.info(f"✅ Найден {result.sku}: {result.price}₽")
                    else:
                        with self.lock:
                            self.error_count += 1
                    
                    # Прогресс каждые 50 категорий
                    if self.processed_count % 50 == 0:
                        progress = (self.processed_count / len(category_urls)) * 100
                        elapsed = time.time() - start_time
                        rate = self.processed_count / elapsed if elapsed > 0 else 0
                        
                        with self.lock:
                            self.logger.info(f"Прогресс: {self.processed_count}/{len(category_urls)} категорий ({progress:.1f}%) - {rate:.1f} кат/сек")
                            self.logger.info(f"Найдено товаров: {len(all_results)}")
                            if target_skus:
                                found_skus = {r.sku for r in all_results}
                                found_count = len(found_skus & target_skus)
                                self.logger.info(f"Найдено целевых товаров: {found_count}/{len(target_skus)}")
                
                except Exception as e:
                    with self.lock:
                        self.error_count += 1
                        self.logger.error(f"Ошибка обработки категории {url}: {e}")
                
                # Задержка между запросами
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
        
        elapsed = time.time() - start_time
        rate = len(category_urls) / elapsed if elapsed > 0 else 0
        
        self.logger.info(f"Парсинг завершен за {elapsed:.1f}с")
        self.logger.info(f"Скорость: {rate:.1f} категорий/сек")
        self.logger.info(f"Найдено уникальных товаров: {len(set(r.sku for r in all_results))}")
        
        # Удаляем дубликаты по SKU
        unique_results = {}
        for result in all_results:
            if result.sku not in unique_results:
                unique_results[result.sku] = result
        
        return list(unique_results.values())
    
    def save_results(self, results: List[ProductInfo], output_file: str):
        """Сохраняет результаты в CSV"""
        
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

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Saturn Sitemap Parser')
    parser.add_argument('--output', default='output/saturn_sitemap_prices.csv', help='Выходной файл')
    parser.add_argument('--workers', type=int, default=20, help='Количество потоков')
    parser.add_argument('--delay', type=float, default=0.1, help='Задержка между запросами (сек)')
    parser.add_argument('--target-skus', nargs='+', help='Конкретные SKU для поиска')
    parser.add_argument('--max-products', type=int, help='Максимальное количество товаров для парсинга')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    saturn_parser = SaturnSitemapParser(
        max_workers=args.workers,
        request_delay=args.delay
    )
    
    # Получаем URL товаров из sitemap
    product_urls = saturn_parser.get_product_urls_from_sitemap()
    
    if not product_urls:
        print("❌ Товары не найдены в sitemap")
        return 1
    
    # Ограничиваем количество если указано
    if args.max_products:
        product_urls = product_urls[:args.max_products]
        print(f"Ограничиваем до {args.max_products} товаров")
    
    # Подготавливаем целевые SKU
    target_skus = None
    if args.target_skus:
        target_skus = set(sku.replace('тов-', '') for sku in args.target_skus)
        print(f"Ищем конкретные SKU: {target_skus}")
    
    # Парсим товары
    results = saturn_parser.parse_products_batch(product_urls, target_skus)
    
    if results:
        saturn_parser.save_results(results, args.output)
        
        print(f"\n✅ РЕЗУЛЬТАТЫ:")
        print(f"Найдено товаров: {len(results)}")
        
        if target_skus:
            found_skus = {r.sku for r in results}
            missing_skus = target_skus - found_skus
            
            print(f"Найдено из целевых: {len(found_skus)}/{len(target_skus)}")
            
            if missing_skus:
                print(f"Не найдено: {', '.join(list(missing_skus)[:10])}")
        
        return 0
    else:
        print("❌ Товары не найдены")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
