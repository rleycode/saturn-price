#!/usr/bin/env python3
"""
Исследование sitemap и альтернативных способов доступа к товарам Saturn
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import re
import logging
from typing import List, Set

class SaturnSitemapExplorer:
    
    def __init__(self):
        self.base_url = "https://msk.saturn.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger = logging.getLogger(__name__)
        
    def check_robots_txt(self):
        """Проверяет robots.txt для поиска sitemap"""
        
        try:
            robots_url = f"{self.base_url}/robots.txt"
            self.logger.info(f"Проверяем robots.txt: {robots_url}")
            
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                print("📄 robots.txt найден:")
                print(content[:500] + "..." if len(content) > 500 else content)
                
                # Ищем sitemap
                sitemap_urls = re.findall(r'Sitemap:\s*(.+)', content, re.IGNORECASE)
                if sitemap_urls:
                    print(f"\n🗺️ Найдены sitemap URLs:")
                    for url in sitemap_urls:
                        print(f"  - {url.strip()}")
                    return [url.strip() for url in sitemap_urls]
                else:
                    print("❌ Sitemap не найден в robots.txt")
            else:
                print(f"❌ robots.txt недоступен: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки robots.txt: {e}")
        
        return []
    
    def check_common_sitemap_urls(self):
        """Проверяет стандартные URL для sitemap"""
        
        common_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/sitemaps/sitemap.xml",
            f"{self.base_url}/sitemap/sitemap.xml"
        ]
        
        found_sitemaps = []
        
        for url in common_urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ Найден sitemap: {url}")
                    found_sitemaps.append(url)
                else:
                    print(f"❌ {url}: {response.status_code}")
            except Exception as e:
                print(f"❌ {url}: {e}")
        
        return found_sitemaps
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Парсит sitemap и извлекает URL товаров"""
        
        try:
            self.logger.info(f"Парсим sitemap: {sitemap_url}")
            
            response = self.session.get(sitemap_url, timeout=15)
            response.raise_for_status()
            
            # Пробуем парсить как XML
            try:
                root = ET.fromstring(response.content)
                
                # Ищем URL в sitemap
                urls = []
                
                # Обрабатываем sitemap index
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        urls.append(loc.text)
                
                # Обрабатываем обычный sitemap
                for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        urls.append(loc.text)
                
                print(f"📊 Найдено {len(urls)} URL в sitemap")
                
                # Фильтруем URL товаров
                product_urls = []
                for url in urls:
                    if '/catalog/' in url and url.count('/') > 4:  # Предполагаем что товары имеют глубокую структуру
                        product_urls.append(url)
                
                print(f"🛍️ Из них товаров: {len(product_urls)}")
                
                # Показываем примеры
                for i, url in enumerate(product_urls[:5]):
                    print(f"  {i+1}. {url}")
                
                return product_urls
                
            except ET.ParseError:
                print("❌ Не удалось распарсить как XML")
                return []
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга sitemap: {e}")
            return []
    
    def find_ajax_endpoints(self):
        """Ищет AJAX endpoints для загрузки товаров"""
        
        try:
            # Проверяем главную страницу каталога
            catalog_url = f"{self.base_url}/catalog/"
            response = self.session.get(catalog_url, timeout=15)
            response.raise_for_status()
            
            content = response.text
            
            # Ищем AJAX URL в JavaScript
            ajax_patterns = [
                r'ajax["\']?\s*:\s*["\']([^"\']+)["\']',
                r'url["\']?\s*:\s*["\']([^"\']*ajax[^"\']*)["\']',
                r'["\']([^"\']*\/ajax\/[^"\']*)["\']',
                r'["\']([^"\']*\.php\?[^"\']*)["\']'
            ]
            
            found_endpoints = set()
            
            for pattern in ajax_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match and ('catalog' in match.lower() or 'product' in match.lower() or 'ajax' in match.lower()):
                        full_url = urljoin(self.base_url, match)
                        found_endpoints.add(full_url)
            
            if found_endpoints:
                print(f"🔍 Найдены потенциальные AJAX endpoints:")
                for endpoint in list(found_endpoints)[:10]:
                    print(f"  - {endpoint}")
            else:
                print("❌ AJAX endpoints не найдены")
            
            return list(found_endpoints)
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска AJAX endpoints: {e}")
            return []
    
    def explore_category_structure(self):
        """Исследует структуру категорий на сайте"""
        
        try:
            # Проверяем главную страницу
            main_url = f"{self.base_url}/"
            response = self.session.get(main_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем ссылки на категории
            category_links = set()
            
            # Различные селекторы для меню и категорий
            selectors = [
                'a[href*="/catalog/"]',
                '.menu a',
                '.navigation a',
                '.category a',
                'nav a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and '/catalog/' in href:
                        full_url = urljoin(self.base_url, href)
                        text = link.get_text(strip=True)
                        if text and len(text) > 2:
                            category_links.add((full_url, text))
            
            print(f"📂 Найдено {len(category_links)} категорий:")
            for i, (url, text) in enumerate(list(category_links)[:10]):
                print(f"  {i+1}. {text} - {url}")
            
            return list(category_links)
            
        except Exception as e:
            self.logger.error(f"Ошибка исследования категорий: {e}")
            return []

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    explorer = SaturnSitemapExplorer()
    
    print("🔍 ИССЛЕДОВАНИЕ АЛЬТЕРНАТИВНЫХ СПОСОБОВ ДОСТУПА К ТОВАРАМ SATURN")
    print("="*70)
    
    # 1. Проверяем robots.txt
    print("\n1️⃣ ПРОВЕРКА ROBOTS.TXT")
    print("-" * 30)
    sitemap_urls = explorer.check_robots_txt()
    
    # 2. Проверяем стандартные URL sitemap
    print("\n2️⃣ ПРОВЕРКА СТАНДАРТНЫХ SITEMAP URL")
    print("-" * 40)
    common_sitemaps = explorer.check_common_sitemap_urls()
    
    all_sitemaps = sitemap_urls + common_sitemaps
    
    # 3. Парсим найденные sitemap
    if all_sitemaps:
        print(f"\n3️⃣ ПАРСИНГ SITEMAP ({len(all_sitemaps)} найдено)")
        print("-" * 30)
        
        all_product_urls = []
        for sitemap_url in all_sitemaps[:3]:  # Парсим первые 3
            product_urls = explorer.parse_sitemap(sitemap_url)
            all_product_urls.extend(product_urls)
        
        if all_product_urls:
            print(f"\n✅ Всего найдено товаров в sitemap: {len(all_product_urls)}")
    
    # 4. Ищем AJAX endpoints
    print(f"\n4️⃣ ПОИСК AJAX ENDPOINTS")
    print("-" * 25)
    ajax_endpoints = explorer.find_ajax_endpoints()
    
    # 5. Исследуем структуру категорий
    print(f"\n5️⃣ ИССЛЕДОВАНИЕ КАТЕГОРИЙ")
    print("-" * 25)
    categories = explorer.explore_category_structure()
    
    # Выводы
    print(f"\n💡 ВЫВОДЫ И РЕКОМЕНДАЦИИ:")
    print("="*30)
    
    if all_sitemaps:
        print("✅ Найдены sitemap - используйте их для получения URL товаров")
    else:
        print("❌ Sitemap не найдены")
    
    if ajax_endpoints:
        print("✅ Найдены AJAX endpoints - можно попробовать их для загрузки товаров")
    else:
        print("❌ AJAX endpoints не найдены")
    
    if categories:
        print("✅ Найдены категории - обходите каждую категорию отдельно")
        print("💡 Рекомендация: Модифицируйте catalog_crawler для обхода всех категорий")
    else:
        print("❌ Категории не найдены")

if __name__ == "__main__":
    main()
