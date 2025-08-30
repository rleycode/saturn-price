#!/usr/bin/env python3

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from fast_saturn_parser import FastSaturnParser

def debug_407_price():
    """Исследуем проблему с повторяющейся ценой 407.0₽"""
    
    # SKU которые показывают цену 407.0₽ из логов
    problem_skus = ["216212", "205897", "190081", "192633", "190080", "145983"]
    
    print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ С ЦЕНОЙ 407.0₽")
    print("=" * 50)
    
    parser = FastSaturnParser()
    
    for sku in problem_skus:
        print(f"\n🧐 Исследуем SKU: {sku}")
        print("-" * 40)
        
        try:
            # Проверяем поисковую страницу
            search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={sku}"
            print(f"🔗 Поисковый URL: {search_url}")
            
            response = parser.session.get(search_url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Проверяем прямой поиск в контейнерах
                product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
                print(f"📦 Найдено контейнеров товаров: {len(product_items)}")
                
                found_direct = False
                for i, item in enumerate(product_items):
                    article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                    if article_elem:
                        article_text = article_elem.get_text(strip=True)
                        expected_article = f"тов-{sku}"
                        if expected_article in article_text:
                            print(f"✅ Найден ПРЯМО в контейнере {i+1}: {article_text}")
                            
                            price_elem = item.find('span', class_='js-price-value')
                            if price_elem and price_elem.get('data-price'):
                                price = price_elem.get('data-price')
                                print(f"💰 Цена из контейнера: {price}₽")
                                found_direct = True
                                break
                
                if not found_direct:
                    print("❌ НЕ найден в прямом поиске")
                
                # Проверяем поиск по ссылкам
                page_text = soup.get_text()
                if "найдено:" in page_text.lower() and "товар" in page_text.lower():
                    import re
                    from urllib.parse import urljoin
                    
                    product_links = soup.find_all('a', href=re.compile(r'/catalog/[^/]+/[^/]+/$'))
                    print(f"🔗 Найдено ссылок на товары: {len(product_links)}")
                    
                    for i, link in enumerate(product_links):
                        link_text = link.get_text(strip=True).lower()
                        href = link.get('href')
                        
                        if (sku in link_text or 
                            f"тов-{sku}" in link_text or
                            any(keyword in link_text for keyword in ["брусок", "строганый", "сухой"])):
                            
                            print(f"🎯 Найдена подходящая ссылка {i+1}: {link_text}")
                            print(f"🔗 URL: {href}")
                            
                            if not href.startswith('http'):
                                product_url = urljoin("https://nnv.saturn.net", href)
                            else:
                                product_url = href
                            
                            # Переходим на страницу товара
                            product_response = parser.session.get(product_url, timeout=10)
                            if product_response.status_code == 200:
                                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                                price_elements = product_soup.find_all(attrs={'data-price': True})
                                
                                if price_elements:
                                    price_value = price_elements[0].get('data-price')
                                    print(f"💰 Цена со страницы товара: {price_value}₽")
                                    
                                    # Проверяем название товара
                                    for tag in ['h1', 'h2', 'title']:
                                        title_elem = product_soup.find(tag)
                                        if title_elem:
                                            name = title_elem.get_text(strip=True)
                                            if len(name) > 10:
                                                print(f"📝 Название: {name}")
                                                break
                                    
                                    # Проверяем артикул на странице товара
                                    page_content = product_soup.get_text()
                                    if f"тов-{sku}" in page_content:
                                        print("✅ Артикул подтвержден на странице товара")
                                    else:
                                        print("⚠️ ВНИМАНИЕ: Артикул НЕ найден на странице товара!")
                                        print("🚨 ВОЗМОЖНО НЕПРАВИЛЬНЫЙ ТОВАР!")
                                
                            break
                
            else:
                print(f"❌ Ошибка запроса: {response.status_code}")
                
        except Exception as e:
            print(f"💥 ОШИБКА: {e}")

if __name__ == "__main__":
    debug_407_price()
