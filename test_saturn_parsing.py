#!/usr/bin/env python3
"""
Тестирование парсинга цен с сайта Saturn для конкретного товара
"""

import requests
from bs4 import BeautifulSoup
import re
import time

def test_saturn_parsing():
    """Тестируем парсинг цены для товара тов-114289"""
    
    # Артикул без префикса для поиска
    article = "114289"
    
    # URL поиска на Saturn
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={article}"
    
    print(f"🔍 Тестируем парсинг для артикула: {article}")
    print(f"URL: {search_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("\n📡 Отправляем запрос...")
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Ответ получен: {response.status_code}")
        print(f"Размер контента: {len(response.content)} байт")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем все возможные варианты цен
        print("\n🔍 Поиск цен различными способами:")
        
        # 1. data-price атрибуты
        print("\n1️⃣ Поиск по data-price:")
        price_elements = soup.find_all(attrs={'data-price': True})
        for elem in price_elements[:5]:  # Первые 5
            print(f"  data-price='{elem.get('data-price')}' в теге {elem.name}")
        
        # 2. Классы с ценами
        print("\n2️⃣ Поиск по классам цен:")
        price_classes = ['price', 'cost', 'amount', 'rub']
        for cls in price_classes:
            elements = soup.find_all(class_=re.compile(cls, re.I))
            for elem in elements[:3]:  # Первые 3 для каждого класса
                text = elem.get_text(strip=True)
                if text and any(c.isdigit() for c in text):
                    print(f"  Класс '{cls}': {text}")
        
        # 3. Поиск по тексту с рублями
        print("\n3️⃣ Поиск текста с рублями:")
        rub_pattern = r'(\d+(?:[,.]?\d+)?)\s*(?:₽|руб|rub)'
        all_text = soup.get_text()
        rub_matches = re.findall(rub_pattern, all_text, re.IGNORECASE)
        unique_prices = list(set(rub_matches))[:10]  # Уникальные цены
        for price in unique_prices:
            print(f"  Найдена цена: {price}₽")
        
        # 4. Специфичный поиск для Saturn
        print("\n4️⃣ Специфичный поиск Saturn:")
        
        # Поиск карточек товаров
        product_cards = soup.find_all(['div', 'article'], class_=re.compile(r'product|item|card', re.I))
        print(f"  Найдено карточек товаров: {len(product_cards)}")
        
        for i, card in enumerate(product_cards[:3]):
            print(f"\n  📦 Карточка {i+1}:")
            
            # Название товара
            title_elem = card.find(['h1', 'h2', 'h3', 'a'], class_=re.compile(r'title|name', re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)
                print(f"    Название: {title[:60]}...")
            
            # Артикул
            article_elem = card.find(text=re.compile(r'артикул|арт', re.I))
            if article_elem:
                print(f"    Артикул найден: {article_elem.strip()}")
            
            # Цены в карточке
            card_prices = card.find_all(attrs={'data-price': True})
            for price_elem in card_prices:
                print(f"    data-price: {price_elem.get('data-price')}")
            
            # Текст с ценами
            card_text = card.get_text()
            card_rub_matches = re.findall(rub_pattern, card_text, re.IGNORECASE)
            for price in set(card_rub_matches):
                print(f"    Цена в тексте: {price}₽")
        
        # 5. Поиск по ID и специфичным селекторам
        print("\n5️⃣ Поиск по специфичным селекторам:")
        
        specific_selectors = [
            '[data-price]',
            '.price',
            '.cost', 
            '.amount',
            '#price',
            '[class*="price"]',
            '[class*="cost"]'
        ]
        
        for selector in specific_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    print(f"  Селектор '{selector}': {len(elements)} элементов")
                    for elem in elements[:2]:
                        text = elem.get_text(strip=True)
                        data_price = elem.get('data-price', '')
                        if text or data_price:
                            print(f"    Текст: '{text}', data-price: '{data_price}'")
            except Exception as e:
                print(f"  Ошибка селектора '{selector}': {e}")
        
        # 6. Сохраняем HTML для анализа
        print(f"\n💾 Сохраняем HTML в файл...")
        with open('saturn_debug.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("  Файл saturn_debug.html создан")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")

if __name__ == "__main__":
    test_saturn_parsing()
