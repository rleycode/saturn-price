#!/usr/bin/env python3
"""
Диагностика структуры страниц категорий Saturn
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

def get_sample_category_urls():
    """Получаем образцы URL категорий из sitemap"""
    
    sitemap_urls = [
        "https://nnv.saturn.net/sitemap.xml",
        "https://nnv.saturn.net/sitemaps/nnv.sitemap.xml"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    all_product_urls = set()
    
    for sitemap_url in sitemap_urls:
        try:
            response = session.get(sitemap_url, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            urls = []
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    urls.append(loc.text)
            
            # Фильтруем URL товаров
            product_urls = []
            for url in urls:
                if '/catalog/' in url:
                    catalog_part = url.split('/catalog/', 1)[1]
                    slash_count = catalog_part.count('/')
                    
                    if slash_count >= 2:
                        product_urls.append(url)
            
            all_product_urls.update(product_urls)
            
        except Exception as e:
            print(f"❌ Ошибка загрузки sitemap {sitemap_url}: {e}")
    
    return list(all_product_urls)[:5]  # Берем только первые 5 для анализа

def analyze_category_structure(urls):
    """Анализируем структуру страниц категорий"""
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    for i, url in enumerate(urls, 1):
        print(f"\n{'='*60}")
        print(f"🔍 АНАЛИЗ КАТЕГОРИИ {i}: {url}")
        print(f"{'='*60}")
        
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Проверяем заголовок
            title = soup.find('title')
            if title:
                print(f"📄 Title: {title.get_text(strip=True)}")
            
            # Ищем различные контейнеры товаров
            selectors_to_check = [
                'div.h_s_list_categor_item_wrap',
                'div.catalog-item',
                'div.product-item',
                'div.item',
                '.product',
                '.goods-item',
                '[data-product]'
            ]
            
            print(f"\n🔍 ПОИСК КОНТЕЙНЕРОВ ТОВАРОВ:")
            
            for selector in selectors_to_check:
                containers = soup.select(selector)
                print(f"   {selector}: {len(containers)} элементов")
                
                if containers and len(containers) <= 5:  # Показываем детали только если элементов немного
                    for j, container in enumerate(containers[:3], 1):
                        print(f"      Элемент {j}: {container.name} class='{container.get('class', [])}'")
                        text_preview = container.get_text(strip=True)[:100]
                        print(f"      Текст: {text_preview}...")
            
            # Ищем артикулы в тексте страницы
            page_text = soup.get_text()
            import re
            articles = re.findall(r'тов-(\d+)', page_text, re.IGNORECASE)
            print(f"\n🏷️  АРТИКУЛЫ В ТЕКСТЕ: {len(set(articles))} уникальных")
            if articles:
                unique_articles = list(set(articles))[:10]
                print(f"   Примеры: {', '.join(unique_articles)}")
            
            # Ищем цены
            price_matches = re.findall(r'(\d+[,.]?\d*)\s*₽', page_text)
            print(f"\n💰 ЦЕНЫ В ТЕКСТЕ: {len(price_matches)} найдено")
            if price_matches:
                unique_prices = list(set(price_matches))[:10]
                print(f"   Примеры: {', '.join(unique_prices)}₽")
            
            # Проверяем все div элементы с классами
            all_divs = soup.find_all('div', class_=True)
            class_counts = {}
            for div in all_divs:
                classes = div.get('class', [])
                for cls in classes:
                    if 'item' in cls.lower() or 'product' in cls.lower() or 'goods' in cls.lower():
                        class_counts[cls] = class_counts.get(cls, 0) + 1
            
            if class_counts:
                print(f"\n📦 ПОТЕНЦИАЛЬНЫЕ КЛАССЫ ТОВАРОВ:")
                for cls, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"   .{cls}: {count} элементов")
            
            # Сохраняем HTML для анализа
            filename = f"debug_category_{i}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"\n💾 HTML сохранен: {filename}")
            
        except Exception as e:
            print(f"❌ Ошибка анализа {url}: {e}")

def main():
    print("🔍 ДИАГНОСТИКА СТРУКТУРЫ СТРАНИЦ КАТЕГОРИЙ")
    print("=" * 50)
    
    # Получаем URL категорий
    category_urls = get_sample_category_urls()
    
    if not category_urls:
        print("❌ Категории не найдены в sitemap")
        return 1
    
    print(f"📊 Анализируем {len(category_urls)} категорий")
    
    # Анализируем структуру
    analyze_category_structure(category_urls)
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
