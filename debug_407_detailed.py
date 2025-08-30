#!/usr/bin/env python3

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from fast_saturn_parser import FastSaturnParser
from bs4 import BeautifulSoup
import requests

def debug_407_detailed():
    """Детальная диагностика проблемы с ценой 407₽"""
    
    # Один проблемный SKU для детального анализа
    sku = "216212"
    
    print(f"🔬 ДЕТАЛЬНАЯ ДИАГНОСТИКА SKU: {sku}")
    print("=" * 50)
    
    parser = FastSaturnParser()
    
    # Проверяем поисковую страницу
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={sku}"
    print(f"🔗 Поисковый URL: {search_url}")
    
    response = parser.session.get(search_url, timeout=10)
    if response.status_code != 200:
        print(f"❌ Ошибка запроса: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Проверяем есть ли результаты поиска
    page_text = soup.get_text()
    if "найдено:" in page_text.lower() and "товар" in page_text.lower():
        print("✅ Найдена страница результатов поиска")
        
        import re
        from urllib.parse import urljoin
        
        product_links = soup.find_all('a', href=re.compile(r'/catalog/[^/]+/[^/]+/$'))
        print(f"🔗 Найдено ссылок на товары: {len(product_links)}")
        
        for i, link in enumerate(product_links):
            link_text = link.get_text(strip=True).lower()
            href = link.get('href')
            
            print(f"\n--- ССЫЛКА {i+1} ---")
            print(f"Текст: '{link_text}'")
            print(f"URL: {href}")
            
            # Проверяем условие поиска
            if (sku in link_text or f"тов-{sku}" in link_text):
                print(f"✅ СОВПАДЕНИЕ! SKU '{sku}' найден в тексте ссылки")
                
                if not href.startswith('http'):
                    product_url = urljoin("https://nnv.saturn.net", href)
                else:
                    product_url = href
                
                print(f"🔗 Полный URL товара: {product_url}")
                
                # Переходим на страницу товара
                product_response = parser.session.get(product_url, timeout=10)
                if product_response.status_code == 200:
                    product_soup = BeautifulSoup(product_response.content, 'html.parser')
                    
                    # Проверяем содержимое страницы товара
                    page_content = product_soup.get_text()
                    expected_article = f"тов-{sku}"
                    
                    print(f"🔍 Ищем артикул '{expected_article}' на странице товара...")
                    
                    if expected_article in page_content:
                        print("✅ АРТИКУЛ НАЙДЕН на странице товара")
                    else:
                        print("❌ АРТИКУЛ НЕ НАЙДЕН на странице товара")
                        print("🔍 Поиск всех упоминаний 'тов-' на странице:")
                        
                        # Ищем все артикулы на странице
                        import re
                        articles = re.findall(r'тов-\d+', page_content)
                        if articles:
                            unique_articles = list(set(articles))
                            print(f"   Найденные артикулы: {unique_articles}")
                        else:
                            print("   Артикулы не найдены")
                    
                    # Проверяем цену
                    price_elements = product_soup.find_all(attrs={'data-price': True})
                    if price_elements:
                        price_value = price_elements[0].get('data-price')
                        print(f"💰 Цена на странице: {price_value}₽")
                        
                        # Проверяем название
                        for tag in ['h1', 'h2', 'title']:
                            title_elem = product_soup.find(tag)
                            if title_elem:
                                name = title_elem.get_text(strip=True)
                                if len(name) > 10:
                                    print(f"📝 Название: {name}")
                                    break
                    
                    # Сохраняем HTML для анализа
                    with open(f"debug_product_{sku}.html", "w", encoding="utf-8") as f:
                        f.write(str(product_soup))
                    print(f"💾 HTML страницы сохранен в debug_product_{sku}.html")
                    
                    break
                else:
                    print(f"❌ Ошибка загрузки страницы товара: {product_response.status_code}")
            else:
                print(f"❌ Нет совпадения с SKU '{sku}'")
    else:
        print("❌ Страница результатов поиска не найдена")

if __name__ == "__main__":
    debug_407_detailed()
