#!/usr/bin/env python3
"""
Поиск конкретного товара тов-114289 в результатах Saturn
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def find_specific_product():
    """Ищем конкретный товар тов-114289"""
    
    article = "114289"
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={article}"
    
    print(f"🔍 Поиск товара с артикулом: {article}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Страница загружена, размер: {len(response.content)} байт")
        
        # Ищем товар по названию "Брусок сухой строганый"
        target_keywords = ["брусок", "сухой", "строганый", "18", "20", "30", "3000"]
        
        print(f"\n🎯 Поиск по ключевым словам: {target_keywords}")
        
        # Поиск всех ссылок на товары
        product_links = soup.find_all('a', href=re.compile(r'/catalog/.*'))
        
        print(f"Найдено ссылок на товары: {len(product_links)}")
        
        candidates = []
        
        for link in product_links:
            link_text = link.get_text(strip=True).lower()
            href = link.get('href', '')
            
            # Проверяем наличие ключевых слов
            matches = sum(1 for keyword in target_keywords if keyword in link_text)
            
            if matches >= 3:  # Минимум 3 совпадения
                candidates.append({
                    'text': link.get_text(strip=True),
                    'href': href,
                    'matches': matches,
                    'element': link
                })
        
        print(f"\n📋 Найдено кандидатов: {len(candidates)}")
        
        # Сортируем по количеству совпадений
        candidates.sort(key=lambda x: x['matches'], reverse=True)
        
        for i, candidate in enumerate(candidates[:5]):
            print(f"\n🏆 Кандидат {i+1} (совпадений: {candidate['matches']}):")
            print(f"  Название: {candidate['text']}")
            print(f"  Ссылка: {candidate['href']}")
            
            # Ищем цену рядом с этим товаром
            parent = candidate['element'].parent
            if parent:
                # Поиск цены в родительском элементе
                price_elements = parent.find_all(attrs={'data-price': True})
                for price_elem in price_elements:
                    price_value = price_elem.get('data-price')
                    print(f"  💰 Цена data-price: {price_value}")
                
                # Поиск цены в тексте
                parent_text = parent.get_text()
                rub_pattern = r'(\d+(?:[,.]?\d+)?)\s*(?:₽|руб)'
                prices_in_text = re.findall(rub_pattern, parent_text, re.IGNORECASE)
                for price in set(prices_in_text):
                    print(f"  💰 Цена в тексте: {price}₽")
        
        # Альтернативный поиск: по артикулу в тексте
        print(f"\n🔍 Поиск по артикулу {article} в тексте:")
        
        # Определяем паттерн для цен
        rub_pattern = r'(\d+(?:[,.]?\d+)?)\s*(?:₽|руб)'
        
        # Ищем все упоминания артикула
        article_pattern = rf'\b{article}\b'
        page_text = soup.get_text()
        
        if re.search(article_pattern, page_text):
            print(f"  ✅ Артикул {article} найден на странице!")
            
            # Ищем контекст вокруг артикула
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if re.search(article_pattern, line):
                    print(f"  📍 Строка {i}: {line.strip()}")
                    
                    # Проверяем соседние строки на наличие цен
                    context_lines = lines[max(0, i-3):i+4]
                    for j, context_line in enumerate(context_lines):
                        prices = re.findall(rub_pattern, context_line, re.IGNORECASE)
                        if prices:
                            print(f"    💰 Цена в контексте: {prices}")
        else:
            print(f"  ❌ Артикул {article} НЕ найден в тексте страницы")
        
        # Проверяем, может быть товар в другом формате
        print(f"\n🔍 Поиск альтернативных форматов артикула:")
        
        alt_formats = [
            f"тов-{article}",
            f"тов {article}",
            f"арт. {article}",
            f"артикул {article}",
            f"#{article}"
        ]
        
        for alt_format in alt_formats:
            if alt_format.lower() in page_text.lower():
                print(f"  ✅ Найден формат: {alt_format}")
            else:
                print(f"  ❌ Не найден: {alt_format}")
        
        # Попробуем прямую ссылку на товар
        print(f"\n🎯 Попробуем найти прямую ссылку на товар...")
        
        # Поиск в JSON данных на странице
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and article in script.string:
                print(f"  ✅ Артикул найден в JavaScript!")
                # Попытка извлечь JSON
                try:
                    # Ищем JSON с товарами
                    json_match = re.search(r'(\{.*"' + article + r'".*\})', script.string)
                    if json_match:
                        print(f"  📊 JSON данные найдены")
                except:
                    pass
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    find_specific_product()
