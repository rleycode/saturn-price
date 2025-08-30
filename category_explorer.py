#!/usr/bin/env python3
"""
Исследование структуры каталога Saturn для поиска категорий с товарами
"""

import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import logging

class SaturnCategoryExplorer:
    
    def __init__(self):
        self.base_url = "https://msk.saturn.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(__name__)
        
    def explore_main_catalog(self):
        """Исследует главную страницу каталога для поиска категорий"""
        
        try:
            url = f"{self.base_url}/catalog/"
            self.logger.info(f"Исследуем главную страницу каталога: {url}")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем ссылки на категории
            category_links = []
            
            # Различные селекторы для категорий
            selectors = [
                'a[href*="/catalog/"]',
                '.category-link',
                '.menu-item a',
                '.catalog-menu a',
                'nav a[href*="/catalog/"]'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and '/catalog/' in href and href != '/catalog/':
                        full_url = urljoin(self.base_url, href)
                        text = link.get_text(strip=True)
                        if text and len(text) > 2:
                            category_links.append({
                                'url': full_url,
                                'text': text,
                                'selector': selector
                            })
            
            # Убираем дубликаты
            unique_categories = {}
            for cat in category_links:
                if cat['url'] not in unique_categories:
                    unique_categories[cat['url']] = cat
            
            self.logger.info(f"Найдено {len(unique_categories)} уникальных категорий")
            
            for cat in list(unique_categories.values())[:10]:  # Показываем первые 10
                print(f"📂 {cat['text']} - {cat['url']}")
            
            return list(unique_categories.values())
            
        except Exception as e:
            self.logger.error(f"Ошибка исследования каталога: {e}")
            return []
    
    def test_category_products(self, category_url: str, category_name: str):
        """Тестирует категорию на наличие товаров"""
        
        try:
            self.logger.info(f"Тестируем категорию: {category_name}")
            
            response = self.session.get(category_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем товары
            product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            
            if product_items:
                print(f"✅ {category_name}: {len(product_items)} товаров")
                
                # Показываем несколько артикулов
                for i, item in enumerate(product_items[:3]):
                    article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                    if article_elem:
                        article = article_elem.get_text(strip=True)
                        print(f"  {i+1}. {article}")
                
                return len(product_items)
            else:
                print(f"❌ {category_name}: товары не найдены")
                return 0
                
        except Exception as e:
            self.logger.warning(f"Ошибка тестирования категории {category_name}: {e}")
            return 0
    
    def find_pagination_urls(self, base_category_url: str):
        """Ищет URL для пагинации в категории"""
        
        try:
            response = self.session.get(base_category_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем пагинацию
            pagination_links = []
            
            # Различные селекторы для пагинации
            pagination_selectors = [
                '.pagination a',
                '.pager a',
                'a[href*="PAGEN"]',
                '.page-numbers a'
            ]
            
            for selector in pagination_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_category_url, href)
                        pagination_links.append(full_url)
            
            # Генерируем дополнительные URL пагинации
            for page in range(2, 11):  # Страницы 2-10
                if 'PAGEN_1=' in base_category_url:
                    continue
                
                separator = '&' if '?' in base_category_url else '?'
                page_url = f"{base_category_url}{separator}PAGEN_1={page}"
                pagination_links.append(page_url)
            
            return list(set(pagination_links))  # Убираем дубликаты
            
        except Exception as e:
            self.logger.warning(f"Ошибка поиска пагинации: {e}")
            return []

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    explorer = SaturnCategoryExplorer()
    
    print("🔍 ИССЛЕДОВАНИЕ СТРУКТУРЫ КАТАЛОГА SATURN")
    print("="*50)
    
    # Исследуем главную страницу каталога
    categories = explorer.explore_main_catalog()
    
    if not categories:
        print("❌ Категории не найдены, тестируем альтернативные URL")
        
        # Пробуем альтернативные URL
        test_urls = [
            "https://msk.saturn.net/catalog/elektronika/",
            "https://msk.saturn.net/catalog/bytovaya-tekhnika/",
            "https://msk.saturn.net/catalog/kompyutery/",
            "https://msk.saturn.net/catalog/telefony/",
            "https://msk.saturn.net/catalog/audio-video/",
        ]
        
        for url in test_urls:
            count = explorer.test_category_products(url, url.split('/')[-2])
            time.sleep(1)
    else:
        print(f"\n📊 ТЕСТИРОВАНИЕ КАТЕГОРИЙ ({len(categories)} найдено)")
        print("="*50)
        
        # Тестируем первые 5 категорий
        for category in categories[:5]:
            count = explorer.test_category_products(category['url'], category['text'])
            
            if count > 0:
                # Ищем пагинацию для этой категории
                pagination_urls = explorer.find_pagination_urls(category['url'])
                if pagination_urls:
                    print(f"  📄 Найдено {len(pagination_urls)} страниц пагинации")
            
            time.sleep(1)
    
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("- Если найдены категории с товарами, используйте их URL для парсинга")
    print("- Добавьте найденные URL в catalog_crawler.py")
    print("- Используйте пагинацию для обхода всех страниц категорий")

if __name__ == "__main__":
    main()
