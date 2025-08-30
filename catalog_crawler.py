#!/usr/bin/env python3
"""
Альтернативный парсер Saturn - обход каталога по страницам
Решает проблему когда поиск возвращает одни и те же результаты
"""

import requests
from bs4 import BeautifulSoup
import time
import csv
from pathlib import Path
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
import re

@dataclass
class ProductInfo:
    sku: str
    name: str
    price: float
    url: str

class SaturnCatalogCrawler:
    
    def __init__(self, delay: float = 1.0):
        self.base_url = "https://msk.saturn.net"
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        self.logger = logging.getLogger(__name__)
        self.found_products = {}  # sku -> ProductInfo
        
    def get_catalog_pages(self) -> List[str]:
        """Получает список страниц каталога"""
        
        catalog_urls = [
            f"{self.base_url}/catalog/",
            f"{self.base_url}/catalog/?PAGEN_1=2",
            f"{self.base_url}/catalog/?PAGEN_1=3",
            f"{self.base_url}/catalog/?PAGEN_1=4",
            f"{self.base_url}/catalog/?PAGEN_1=5",
        ]
        
        return catalog_urls
    
    def extract_products_from_page(self, url: str) -> List[ProductInfo]:
        """Извлекает товары со страницы каталога"""
        
        try:
            self.logger.info(f"Обрабатываем страницу: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Используем правильные селекторы
            product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            
            products = []
            
            for item in product_items:
                try:
                    # Извлекаем артикул
                    article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                    if not article_elem:
                        continue
                    
                    article_text = article_elem.get_text(strip=True)
                    
                    # Проверяем что это товар Saturn с префиксом "тов-"
                    if not article_text.startswith('тов-'):
                        continue
                    
                    sku = article_text.replace('тов-', '')
                    
                    # Извлекаем название
                    name_elem = item.find('a', class_='h_s_list_categor_item')
                    name = name_elem.get_text(strip=True) if name_elem else f"Товар {sku}"
                    
                    # Извлекаем цену
                    price = None
                    price_elem = item.find('span', class_='shopping_cart_goods_list_item_sum_item')
                    
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price_match = re.search(r'(\d+[,.]?\d*)', price_text)
                        if price_match:
                            try:
                                price = float(price_match.group(1).replace(',', '.'))
                            except ValueError:
                                pass
                    
                    if not price:
                        # Альтернативный поиск цены
                        item_text = item.get_text()
                        price_match = re.search(r'(\d+[,.]?\d*)\s*₽', item_text)
                        if price_match:
                            try:
                                price = float(price_match.group(1).replace(',', '.'))
                            except ValueError:
                                continue
                        else:
                            continue
                    
                    # Получаем URL товара
                    product_url = url
                    if name_elem and name_elem.get('href'):
                        product_url = self.base_url + name_elem.get('href')
                    
                    product = ProductInfo(
                        sku=sku,
                        name=name,
                        price=price,
                        url=product_url
                    )
                    
                    products.append(product)
                    self.logger.info(f"Найден товар: {sku} - {price}₽")
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки товара: {e}")
                    continue
            
            self.logger.info(f"Извлечено {len(products)} товаров со страницы")
            return products
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки страницы {url}: {e}")
            return []
    
    def crawl_catalog(self, target_skus: List[str] = None) -> Dict[str, ProductInfo]:
        """Обходит каталог и собирает товары"""
        
        self.logger.info("Начинаем обход каталога Saturn")
        
        catalog_pages = self.get_catalog_pages()
        all_products = {}
        
        for page_url in catalog_pages:
            products = self.extract_products_from_page(page_url)
            
            for product in products:
                all_products[product.sku] = product
                
                # Если ищем конкретные SKU, проверяем найден ли
                if target_skus and product.sku in target_skus:
                    self.logger.info(f"✅ Найден целевой товар: {product.sku}")
            
            # Пауза между страницами
            time.sleep(self.delay)
        
        self.logger.info(f"Всего найдено товаров: {len(all_products)}")
        
        if target_skus:
            found_count = sum(1 for sku in target_skus if sku in all_products)
            self.logger.info(f"Найдено целевых товаров: {found_count}/{len(target_skus)}")
        
        return all_products
    
    def save_products(self, products: Dict[str, ProductInfo], output_file: str):
        """Сохраняет товары в CSV файл"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['sku', 'name', 'price', 'url'])
            
            for product in products.values():
                writer.writerow([
                    product.sku,
                    product.name,
                    product.price,
                    product.url
                ])
        
        self.logger.info(f"Товары сохранены в {output_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Saturn Catalog Crawler')
    parser.add_argument('--output', default='output/saturn_catalog_products.csv', help='Выходной файл')
    parser.add_argument('--delay', type=float, default=1.0, help='Задержка между страницами (сек)')
    parser.add_argument('--target-skus', nargs='+', help='Конкретные SKU для поиска')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    crawler = SaturnCatalogCrawler(delay=args.delay)
    
    target_skus = args.target_skus
    if target_skus:
        # Убираем префикс "тов-" если он есть
        target_skus = [sku.replace('тов-', '') for sku in target_skus]
    
    products = crawler.crawl_catalog(target_skus)
    
    if products:
        crawler.save_products(products, args.output)
        
        if target_skus:
            print("\n" + "="*50)
            print("РЕЗУЛЬТАТЫ ПОИСКА:")
            print("="*50)
            
            for sku in target_skus:
                if sku in products:
                    product = products[sku]
                    print(f"✅ {sku}: {product.price}₽ - {product.name}")
                else:
                    print(f"❌ {sku}: не найден")
    else:
        print("Товары не найдены")
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
