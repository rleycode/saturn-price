#!/usr/bin/env python3
"""
Прямой доступ к товару по результатам поиска Saturn
"""

import requests
from bs4 import BeautifulSoup
import re

def direct_product_access():
    """Прямой доступ к найденному товару"""
    
    article = "114289"
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={article}"
    
    print(f"🎯 Прямой доступ к товару {article}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Страница загружена")
        
        # Поиск результата "1 товар из 1 категории" означает точное совпадение
        print(f"\n🔍 Поиск единственного товара в результатах...")
        
        # 1. Ищем первый товар в результатах поиска
        # Обычно это элементы с классами product, item, card и т.д.
        product_selectors = [
            '.catalog-item',
            '.product-item', 
            '.item',
            '.product',
            '[data-product]',
            '.card'
        ]
        
        found_product = None
        
        for selector in product_selectors:
            products = soup.select(selector)
            if products:
                print(f"  Найдено {len(products)} элементов по селектору '{selector}'")
                found_product = products[0]  # Берем первый
                break
        
        if not found_product:
            # Альтернативный поиск - любой элемент с data-price
            price_elements = soup.find_all(attrs={'data-price': True})
            if price_elements:
                print(f"  Найдено {len(price_elements)} элементов с data-price")
                # Ищем родительский элемент товара
                for price_elem in price_elements:
                    parent = price_elem.parent
                    while parent and parent.name != 'body':
                        # Проверяем, есть ли в родителе ссылка на товар
                        product_link = parent.find('a', href=re.compile(r'/catalog/'))
                        if product_link:
                            found_product = parent
                            print(f"  Найден товар через data-price элемент")
                            break
                        parent = parent.parent
                    if found_product:
                        break
        
        if found_product:
            print(f"\n📦 Анализ найденного товара:")
            
            # Название товара
            title_selectors = ['h1', 'h2', 'h3', 'a[href*="/catalog/"]', '.title', '.name']
            for selector in title_selectors:
                title_elem = found_product.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 10:  # Фильтруем короткие тексты
                        print(f"  📝 Название: {title}")
                        break
            
            # Ссылка на товар
            link_elem = found_product.find('a', href=re.compile(r'/catalog/'))
            if link_elem:
                product_url = link_elem.get('href')
                if not product_url.startswith('http'):
                    product_url = 'https://nnv.saturn.net' + product_url
                print(f"  🔗 Ссылка: {product_url}")
            
            # Все цены в элементе товара
            print(f"  💰 Цены:")
            
            # data-price атрибуты
            price_elements = found_product.find_all(attrs={'data-price': True})
            for price_elem in price_elements:
                price_value = price_elem.get('data-price')
                price_text = price_elem.get_text(strip=True)
                print(f"    data-price: {price_value} (текст: '{price_text}')")
            
            # Поиск цен в тексте
            product_text = found_product.get_text()
            
            # Различные паттерны цен
            price_patterns = [
                r'(\d+)\s*₽',  # 99₽
                r'(\d+)\s*руб',  # 99 руб
                r'С картой\s*(\d+)\s*₽',  # С картой 92₽
                r'Без карты\s*(\d+)\s*₽',  # Без карты 99₽
                r'(\d+(?:[,.]?\d+)?)\s*(?:₽|руб)',  # Общий паттерн
            ]
            
            all_found_prices = set()
            
            for pattern in price_patterns:
                matches = re.findall(pattern, product_text, re.IGNORECASE)
                for match in matches:
                    all_found_prices.add(match)
            
            for price in sorted(all_found_prices):
                print(f"    Цена в тексте: {price}₽")
            
            # Если есть ссылка, переходим на страницу товара
            if 'product_url' in locals():
                print(f"\n🔗 Переходим на страницу товара...")
                try:
                    product_response = requests.get(product_url, headers=headers, timeout=30)
                    product_response.raise_for_status()
                    
                    product_soup = BeautifulSoup(product_response.content, 'html.parser')
                    
                    print(f"✅ Страница товара загружена")
                    
                    # Поиск цен на странице товара
                    print(f"  💰 Цены на странице товара:")
                    
                    # data-price на странице товара
                    product_prices = product_soup.find_all(attrs={'data-price': True})
                    for price_elem in product_prices:
                        price_value = price_elem.get('data-price')
                        print(f"    data-price: {price_value}")
                    
                    # Поиск специфичных элементов цен
                    price_classes = ['.price', '.cost', '.amount', '[class*="price"]']
                    for price_class in price_classes:
                        price_elements = product_soup.select(price_class)
                        for elem in price_elements[:3]:  # Первые 3
                            text = elem.get_text(strip=True)
                            if any(c.isdigit() for c in text):
                                print(f"    {price_class}: {text}")
                    
                    # Поиск текста "С картой" и "Без карты"
                    page_text = product_soup.get_text()
                    card_patterns = [
                        r'С картой[^\d]*(\d+)[^\d]*₽',
                        r'Без карты[^\d]*(\d+)[^\d]*₽',
                        r'(\d+)\s*₽[^\d]*С картой',
                        r'(\d+)\s*₽[^\d]*Без карты'
                    ]
                    
                    for pattern in card_patterns:
                        matches = re.findall(pattern, page_text, re.IGNORECASE)
                        if matches:
                            print(f"    Найдена цена по паттерну '{pattern}': {matches}")
                    
                except Exception as e:
                    print(f"    ❌ Ошибка загрузки страницы товара: {e}")
        
        else:
            print(f"❌ Товар не найден в результатах поиска")
            
            # Дополнительная диагностика
            print(f"\n🔍 Дополнительная диагностика:")
            
            # Ищем любые элементы с ценами
            all_prices = soup.find_all(attrs={'data-price': True})
            print(f"  Всего элементов с data-price: {len(all_prices)}")
            
            if all_prices:
                print(f"  Первые 5 цен:")
                for i, price_elem in enumerate(all_prices[:5]):
                    price_value = price_elem.get('data-price')
                    print(f"    {i+1}. {price_value}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    direct_product_access()
