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
    parsed_at: Optional[datetime] = None

class FastSaturnParser:
    
    def __init__(self, max_workers: int = 10, request_delay: float = 0.1):
        self.base_url = "https://msk.saturn.net"
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
            # Сначала пробуем прямой поиск на странице поиска
            url = f"{self.search_url}{sku}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Метод 1: Прямой поиск в контейнерах товаров
            product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            for item in product_items:
                article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                if not article_elem:
                    continue
                
                article_text = article_elem.get_text(strip=True)
                expected_article = f"тов-{sku}"
                if expected_article not in article_text:
                    continue
                
                name_elem = item.find('p', class_='h_s_list_categor_item_txt')
                name = name_elem.get_text(strip=True) if name_elem else f"Товар {sku}"
                
                price_elem = item.find('span', class_='js-price-value')
                if price_elem and price_elem.get('data-price'):
                    try:
                        price = float(price_elem.get('data-price'))
                        return ProductPrice(
                            sku=sku,
                            name=name,
                            price=price,
                            old_price=None,
                            availability="В наличии",
                            url=url,
                            parsed_at=datetime.now()
                        )
                    except ValueError:
                        continue
            
            # Метод 2: Поиск по ссылкам на товары (как в saturn_parser.py)
            page_text = soup.get_text()
            if "найдено:" in page_text.lower() and "товар" in page_text.lower():
                import re
                from urllib.parse import urljoin
                
                product_links = soup.find_all('a', href=re.compile(r'/catalog/[^/]+/[^/]+/$'))
                
                for link in product_links:
                    link_text = link.get_text(strip=True).lower()
                    href = link.get('href')
                    
                    if (sku in link_text or 
                        f"тов-{sku}" in link_text):
                        
                        if not href.startswith('http'):
                            product_url = urljoin("https://msk.saturn.net", href)
                        else:
                            product_url = href
                        
                        # Переходим на страницу товара
                        product_response = self.session.get(product_url, timeout=10)
                        if product_response.status_code != 200:
                            continue
                        
                        product_soup = BeautifulSoup(product_response.content, 'html.parser')
                        
                        # КРИТИЧЕСКИ ВАЖНО: Проверяем что артикул действительно есть на странице товара
                        page_content = product_soup.get_text()
                        expected_article = f"тов-{sku}"
                        if expected_article not in page_content:
                            # Товар не подтвержден - пропускаем
                            continue
                        
                        price_elements = product_soup.find_all(attrs={'data-price': True})
                        
                        if price_elements:
                            try:
                                price_value = price_elements[0].get('data-price')
                                price = float(price_value)
                                
                                # Ищем название товара
                                name = None
                                for tag in ['h1', 'h2', 'title']:
                                    title_elem = product_soup.find(tag)
                                    if title_elem:
                                        name = title_elem.get_text(strip=True)
                                        if len(name) > 10:
                                            break
                                
                                if not name:
                                    name = link.get_text(strip=True)
                                
                                return ProductPrice(
                                    sku=sku,
                                    name=name,
                                    price=price,
                                    old_price=None,
                                    availability="В наличии",
                                    url=product_url,
                                    parsed_at=datetime.now()
                                )
                                
                            except (ValueError, TypeError):
                                continue
            
            # Метод 3: Поиск по тексту страницы (fallback)
            # Может найти неточные совпадения, но лучше что-то, чем ничего
            import re
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
                            
                            return ProductPrice(
                                sku=sku,
                                name=f"Товар {sku}",
                                price=price,
                                old_price=None,
                                availability="В наличии",
                                url=url,
                                parsed_at=datetime.now()
                            )
                        except (ValueError, TypeError):
                            continue
                    
                    current = current.parent
            
            return None
            
        except requests.exceptions.RequestException as e:
            with self.log_lock:
                self.logger.warning(f"Ошибка запроса для {sku}: {e}")
            return None
        except Exception as e:
            with self.log_lock:
                self.logger.error(f"Ошибка парсинга {sku}: {e}")
            return None
    
    def parse_products_batch(self, skus: List[str], output_file: str = None, update_bitrix: bool = True) -> List[ProductPrice]:
        start_time = time.time()
        results = []
        
        # Подключение к Bitrix для обновления цен
        bitrix_client = None
        if update_bitrix:
            try:
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
                bitrix_client = BitrixClient(config)
                bitrix_client.connect()
                self.logger.info("Подключение к Bitrix установлено для обновления цен")
            except Exception as e:
                self.logger.warning(f"Не удалось подключиться к Bitrix: {e}")
                update_bitrix = False
        
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
                        
                        # Обновляем цену в Bitrix напрямую с применением наценки
                        if update_bitrix and bitrix_client:
                            try:
                                article_with_prefix = f"тов-{sku}"
                                product = bitrix_client.get_product_by_article(article_with_prefix)
                                if product:
                                    # Применяем наценку к цене
                                    from bitrix_integration import MarkupProcessor
                                    markup_processor = MarkupProcessor(bitrix_client)
                                    final_price, markup_percent = markup_processor.apply_markup(product, result.price)
                                    
                                    # Обновляем финальную цену с наценкой
                                    success = bitrix_client.update_product_price(product.id, final_price)
                                    if success:
                                        with self.log_lock:
                                            self.logger.info(f"✅ Обновлен {sku}: {result.price} → {final_price:.2f} руб. (+{markup_percent:.1f}%)")
                                        
                                        # Запускаем модуль underprice для пересчета скидок
                                        try:
                                            bitrix_client.trigger_underprice_module(product.id)
                                        except Exception as underprice_error:
                                            with self.log_lock:
                                                self.logger.warning(f"Ошибка underprice для {sku}: {underprice_error}")
                                    else:
                                        with self.log_lock:
                                            self.logger.warning(f"❌ Ошибка обновления {sku} в Bitrix")
                                else:
                                    with self.log_lock:
                                        self.logger.warning(f"⚠️ Товар {sku} не найден в Bitrix")
                            except Exception as e:
                                with self.log_lock:
                                    self.logger.error(f"Ошибка обновления {sku} в Bitrix: {e}")
                        else:
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
        
        # Закрываем подключение к Bitrix
        if bitrix_client:
            try:
                bitrix_client.disconnect()
                self.logger.info("Подключение к Bitrix закрыто")
            except:
                pass
        
        if output_file and results:
            self.save_results(results, output_file)
        
        elapsed = time.time() - start_time
        rate = len(skus) / elapsed if elapsed > 0 else 0
        
        self.logger.info(f"Парсинг завершен за {elapsed:.1f}с")
        self.logger.info(f"Скорость: {rate:.1f} товаров/сек")
        self.logger.info(f"Найдено: {self.success_count}/{len(skus)} товаров")
        if update_bitrix:
            self.logger.info(f"Цены обновлены напрямую в Bitrix")
        
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
    results = parser.parse_products_batch(skus, args.output, update_bitrix=True)
    
    return 0 if results else 1


if __name__ == '__main__':
    sys.exit(main())
