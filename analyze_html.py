#!/usr/bin/env python3
"""
Анализ HTML файлов для поиска правильных селекторов
"""

import os
from bs4 import BeautifulSoup
import re

def analyze_html_file(filename):
    """Анализируем HTML файл для поиска товаров"""
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден")
        return
    
    print(f"\n🔍 Анализируем {filename}")
    print("="*50)
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # 1. Ищем различные классы товаров
    possible_item_classes = [
        'catalog-item', 'product-item', 'item', 'product', 
        'goods-item', 'card', 'product-card', 'catalog-card'
    ]
    
    for class_name in possible_item_classes:
        items = soup.find_all('div', class_=class_name)
        if items:
            print(f"✅ Найдено {len(items)} элементов с классом '{class_name}'")
    
    # 2. Ищем элементы с артикулами
    print(f"\n🏷️ Поиск артикулов:")
    
    # Ищем все элементы содержащие числа (потенциальные артикулы)
    all_text = soup.get_text()
    article_patterns = [
        r'тов-\d+',
        r'\d{6}',  # 6-значные числа
        r'артикул[:\s]*(\d+)',
        r'код[:\s]*(\d+)'
    ]
    
    for pattern in article_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        if matches:
            print(f"  📍 Паттерн '{pattern}': найдено {len(matches)} совпадений")
            for match in matches[:5]:  # Показываем первые 5
                print(f"    - {match}")
    
    # 3. Ищем элементы с ценами
    print(f"\n💰 Поиск цен:")
    
    price_patterns = [
        r'\d+[,.]?\d*\s*руб',
        r'\d+[,.]?\d*\s*₽',
        r'data-price="(\d+)"',
        r'price["\s:]*(\d+)'
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        if matches:
            print(f"  💵 Паттерн '{pattern}': найдено {len(matches)} совпадений")
    
    # 4. Анализируем структуру страницы
    print(f"\n📊 Структура страницы:")
    
    # Ищем основные контейнеры
    containers = [
        ('main', 'main'),
        ('content', 'div'),
        ('catalog', 'div'),
        ('products', 'div'),
        ('results', 'div')
    ]
    
    for class_name, tag in containers:
        elements = soup.find_all(tag, class_=lambda x: x and class_name in x.lower() if x else False)
        if elements:
            print(f"  📦 {tag}.{class_name}: {len(elements)} элементов")
    
    # 5. Ищем JavaScript который может загружать товары
    print(f"\n🔧 JavaScript анализ:")
    
    scripts = soup.find_all('script')
    js_keywords = ['ajax', 'fetch', 'catalog', 'products', 'load']
    
    for keyword in js_keywords:
        count = sum(1 for script in scripts if script.string and keyword in script.string.lower())
        if count > 0:
            print(f"  ⚙️ Скриптов с '{keyword}': {count}")
    
    # 6. Проверяем наличие форм поиска
    print(f"\n🔍 Формы поиска:")
    
    forms = soup.find_all('form')
    search_forms = [form for form in forms if form.get('action') and 'search' in form.get('action', '').lower()]
    
    if search_forms:
        print(f"  📝 Найдено форм поиска: {len(search_forms)}")
        for form in search_forms:
            print(f"    - Action: {form.get('action')}")
    
    # 7. Ищем сообщения о пустых результатах
    print(f"\n❌ Проверка на пустые результаты:")
    
    empty_messages = [
        'не найдено', 'нет результатов', 'ничего не найдено',
        'no results', 'not found', 'пусто', 'отсутствует'
    ]
    
    for message in empty_messages:
        if message in all_text.lower():
            print(f"  🚫 Найдено сообщение: '{message}'")

def main():
    """Анализируем все HTML файлы"""
    
    html_files = [f for f in os.listdir('.') if f.startswith('debug_search_') and f.endswith('.html')]
    
    if not html_files:
        print("❌ HTML файлы не найдены")
        return
    
    print(f"📁 Найдено HTML файлов: {len(html_files)}")
    
    for html_file in html_files[:2]:  # Анализируем первые 2 файла
        analyze_html_file(html_file)

if __name__ == "__main__":
    main()
