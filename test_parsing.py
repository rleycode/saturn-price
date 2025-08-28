#!/usr/bin/env python3
"""
Тест парсинга конкретного товара Saturn
"""

import requests
import re
from bs4 import BeautifulSoup

def test_saturn_search(sku):
    """Тестирование поиска товара на Saturn"""
    
    base_url = "https://nnv.saturn.net"
    
    # Различные варианты URL для тестирования
    test_urls = [
        f"{base_url}/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={sku}",
        f"{base_url}/search/?q={sku}",
        f"{base_url}/catalog/?search={sku}",
        f"{base_url}/catalog/?q={sku}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    print(f"🔍 Тестируем поиск товара: {sku}")
    print("=" * 60)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}. Тестируем URL: {url}")
        
        try:
            response = session.get(url, timeout=10)
            print(f"   Статус: {response.status_code}")
            print(f"   Размер ответа: {len(response.text)} символов")
            
            if response.status_code == 200:
                # Ищем ссылки на товары
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Различные селекторы для поиска товаров
                product_selectors = [
                    'a[href*="product"]',
                    'a[href*="item"]', 
                    'a[href*="goods"]',
                    '.product-item a',
                    '.item a',
                    '.goods a',
                    'a[href*="/catalog/"]'
                ]
                
                found_links = []
                for selector in product_selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href', '')
                        if href and (sku in href or sku in link.get_text()):
                            found_links.append(href)
                
                if found_links:
                    print(f"   ✅ Найдено ссылок: {len(found_links)}")
                    for link in found_links[:3]:  # Показываем первые 3
                        if link.startswith('/'):
                            link = base_url + link
                        print(f"      - {link}")
                else:
                    print(f"   ❌ Ссылки на товары не найдены")
                
                # Ищем артикул в тексте страницы
                if sku in response.text:
                    print(f"   ✅ Артикул {sku} найден в тексте страницы")
                else:
                    print(f"   ❌ Артикул {sku} НЕ найден в тексте страницы")
                
                # Сохраняем HTML для анализа
                filename = f"saturn_search_{sku}_{i}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"   💾 HTML сохранен в {filename}")
                
            else:
                print(f"   ❌ Ошибка HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Ошибка запроса: {e}")
    
    print("\n" + "=" * 60)
    print("🔧 Для улучшения парсинга предоставьте:")
    print("1. HTML код страницы поиска (файлы saturn_search_*.html)")
    print("2. Прямую ссылку на товар с артикулом 103516")
    print("3. Скриншот страницы поиска")

if __name__ == "__main__":
    test_saturn_search("103516")
