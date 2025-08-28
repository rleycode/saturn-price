#!/usr/bin/env python3
"""
Отладка извлечения цены из HTML Saturn
"""

import re
from bs4 import BeautifulSoup

def debug_price_extraction():
    """Отладка извлечения цены из сохраненного HTML"""
    
    filename = "saturn_search_103516_1.html"
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html = f.read()
        
        print("🔍 Отладка извлечения цены")
        print("=" * 50)
        
        # 1. Поиск всех цен в HTML
        print("1️⃣ Поиск всех цен в HTML:")
        
        price_patterns = [
            r'(\d+(?:\s?\d+)*(?:[.,]\d+)?)\s*руб',
            r'(\d+(?:\s?\d+)*(?:[.,]\d+)?)\s*₽',
            r'price[^>]*>(\d+(?:\s?\d+)*(?:[.,]\d+)?)',
            r'cost[^>]*>(\d+(?:\s?\d+)*(?:[.,]\d+)?)',
            r'(\d+(?:\s?\d+)*(?:[.,]\d+)?)\s*р\.',
        ]
        
        all_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                price_str = match.replace(' ', '').replace(',', '.')
                try:
                    price = float(price_str)
                    if 10 <= price <= 100000:  # Разумный диапазон цен
                        all_prices.append(price)
                except ValueError:
                    continue
        
        unique_prices = sorted(set(all_prices))
        print(f"   Найдено уникальных цен: {len(unique_prices)}")
        for price in unique_prices[:10]:  # Показываем первые 10
            print(f"   - {price} руб.")
        
        # 2. Поиск контекста вокруг артикула тов-103516
        print(f"\n2️⃣ Контекст вокруг артикула тов-103516:")
        
        # Ищем позицию артикула
        sku_pos = html.find('тов-103516')
        if sku_pos != -1:
            # Берем контекст 1000 символов до и после
            start = max(0, sku_pos - 1000)
            end = min(len(html), sku_pos + 1000)
            context = html[start:end]
            
            print("   Контекст найден, ищем цены в контексте:")
            
            # Ищем цены в контексте
            for pattern in price_patterns:
                matches = re.findall(pattern, context, re.IGNORECASE)
                if matches:
                    print(f"   Паттерн '{pattern}' нашел: {matches}")
        
        # 3. Поиск через BeautifulSoup
        print(f"\n3️⃣ Поиск через BeautifulSoup:")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ищем элементы, содержащие артикул
        elements_with_sku = soup.find_all(text=re.compile('тов-103516'))
        print(f"   Элементов с артикулом: {len(elements_with_sku)}")
        
        for i, element in enumerate(elements_with_sku):
            print(f"   Элемент {i+1}: {str(element).strip()}")
            
            # Ищем родительские элементы
            parent = element.parent
            if parent:
                parent_text = parent.get_text()
                print(f"   Родительский элемент: {parent_text[:200]}...")
                
                # Ищем цены в родительском элементе
                for pattern in price_patterns:
                    matches = re.findall(pattern, parent_text, re.IGNORECASE)
                    if matches:
                        print(f"   🎯 Найдена цена в родителе: {matches}")
        
        # 4. Поиск по классам и атрибутам
        print(f"\n4️⃣ Поиск элементов с ценами по классам:")
        
        price_selectors = [
            '[class*="price"]',
            '[class*="cost"]',
            '[class*="sum"]',
            '[data-price]',
            '.price',
            '.cost'
        ]
        
        for selector in price_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"   Селектор '{selector}': найдено {len(elements)} элементов")
                for elem in elements[:3]:  # Показываем первые 3
                    text = elem.get_text(strip=True)
                    print(f"      - {text}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    debug_price_extraction()
