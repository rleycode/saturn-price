#!/usr/bin/env python3
"""
Диагностика проблемы sitemap_parser - проверяем что возвращают URL из sitemap
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
from urllib.parse import urljoin

def get_sample_urls_from_sitemap():
    """Получаем образцы URL из sitemap для анализа"""
    
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
            print(f"📥 Загружаем sitemap: {sitemap_url}")
            
            response = session.get(sitemap_url, timeout=15)
            response.raise_for_status()
            
            # Парсим XML
            root = ET.fromstring(response.content)
            
            # Извлекаем все URL
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
            
            print(f"📊 Найдено {len(product_urls)} товаров в {sitemap_url}")
            all_product_urls.update(product_urls)
            
        except Exception as e:
            print(f"❌ Ошибка загрузки sitemap {sitemap_url}: {e}")
    
    return list(all_product_urls)

def analyze_product_urls(urls, sample_size=10):
    """Анализируем образцы URL товаров"""
    
    print(f"\n🔍 АНАЛИЗ {sample_size} ОБРАЗЦОВ URL:")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Берем образцы URL
    sample_urls = urls[:sample_size]
    
    for i, url in enumerate(sample_urls, 1):
        print(f"\n{i}. URL: {url}")
        
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Проверяем заголовок страницы
            title = soup.find('title')
            if title:
                print(f"   📄 Title: {title.get_text(strip=True)[:100]}")
            
            # Ищем артикул разными способами
            article_found = False
            
            # Способ 1: специальные селекторы
            article_selectors = [
                'span.article',
                '.product-article', 
                '[data-article]',
                'p.h_s_list_categor_item_articul'
            ]
            
            for selector in article_selectors:
                article_elem = soup.select_one(selector)
                if article_elem:
                    article_text = article_elem.get_text(strip=True)
                    if 'тов-' in article_text:
                        print(f"   🏷️  Артикул ({selector}): {article_text}")
                        article_found = True
                        break
                    elif article_elem.get('data-article'):
                        article_text = article_elem.get('data-article')
                        if 'тов-' in article_text:
                            print(f"   🏷️  Артикул (data-article): {article_text}")
                            article_found = True
                            break
            
            # Способ 2: поиск в тексте страницы
            if not article_found:
                page_text = soup.get_text()
                article_matches = re.findall(r'тов-(\d+)', page_text, re.IGNORECASE)
                if article_matches:
                    print(f"   🏷️  Артикулы в тексте: {article_matches}")
                    article_found = True
            
            if not article_found:
                print(f"   ❌ Артикул не найден")
            
            # Проверяем цену
            price_selectors = [
                '.price',
                '.product-price',
                '[data-price]',
                'span.shopping_cart_goods_list_item_sum_item'
            ]
            
            price_found = False
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    if price_elem.get('data-price'):
                        print(f"   💰 Цена ({selector}): {price_elem.get('data-price')}₽")
                        price_found = True
                        break
                    else:
                        price_text = price_elem.get_text(strip=True)
                        price_match = re.search(r'(\d+[,.]?\d*)', price_text)
                        if price_match:
                            print(f"   💰 Цена ({selector}): {price_match.group(1)}₽")
                            price_found = True
                            break
            
            if not price_found:
                # Ищем цену в тексте
                page_text = soup.get_text()
                price_match = re.search(r'(\d+[,.]?\d*)\s*₽', page_text)
                if price_match:
                    print(f"   💰 Цена в тексте: {price_match.group(1)}₽")
                else:
                    print(f"   ❌ Цена не найдена")
            
            # Проверяем есть ли редирект или одинаковый контент
            if response.history:
                print(f"   🔄 Редирект: {response.url}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

def check_url_patterns(urls):
    """Проверяем паттерны URL"""
    
    print(f"\n📋 АНАЛИЗ ПАТТЕРНОВ URL:")
    print("=" * 30)
    
    # Группируем по паттернам
    patterns = {}
    
    for url in urls[:50]:  # Анализируем первые 50
        # Извлекаем путь после /catalog/
        if '/catalog/' in url:
            path = url.split('/catalog/', 1)[1]
            # Убираем последний сегмент (название товара)
            path_parts = path.split('/')
            if len(path_parts) >= 3:
                category_path = '/'.join(path_parts[:-1])
                if category_path not in patterns:
                    patterns[category_path] = []
                patterns[category_path].append(url)
    
    print(f"Найдено {len(patterns)} различных категорий:")
    
    for i, (pattern, urls_in_pattern) in enumerate(list(patterns.items())[:10], 1):
        print(f"{i}. {pattern} ({len(urls_in_pattern)} товаров)")
        if len(urls_in_pattern) <= 3:
            for url in urls_in_pattern:
                print(f"   - {url}")

def main():
    print("🔍 ДИАГНОСТИКА SITEMAP_PARSER")
    print("=" * 40)
    
    # Получаем URL из sitemap
    product_urls = get_sample_urls_from_sitemap()
    
    if not product_urls:
        print("❌ Товары не найдены в sitemap")
        return 1
    
    print(f"\n📊 Всего найдено товаров: {len(product_urls)}")
    
    # Анализируем паттерны URL
    check_url_patterns(product_urls)
    
    # Анализируем содержимое страниц
    analyze_product_urls(product_urls, sample_size=10)
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
