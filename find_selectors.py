#!/usr/bin/env python3
"""
Поиск правильных CSS селекторов для товаров Saturn
"""

import os
from bs4 import BeautifulSoup
import re

def find_product_structure(filename):
    """Ищем структуру товаров в HTML"""
    
    if not os.path.exists(filename):
        return
    
    print(f"🔍 Анализируем структуру товаров в {filename}")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Ищем все элементы содержащие артикулы "тов-"
    article_pattern = re.compile(r'тов-\d+')
    
    # Ищем все элементы с текстом содержащим артикулы
    elements_with_articles = []
    
    for element in soup.find_all(text=article_pattern):
        parent = element.parent
        if parent:
            elements_with_articles.append(parent)
    
    print(f"📦 Найдено элементов с артикулами: {len(elements_with_articles)}")
    
    if not elements_with_articles:
        return
    
    # Анализируем структуру родительских элементов
    parent_info = {}
    
    for elem in elements_with_articles[:10]:  # Анализируем первые 10
        # Поднимаемся по дереву DOM чтобы найти контейнер товара
        current = elem
        depth = 0
        
        while current and depth < 5:  # Максимум 5 уровней вверх
            if current.name:
                tag_class = current.get('class', [])
                tag_id = current.get('id', '')
                
                key = f"{current.name}.{'.'.join(tag_class) if tag_class else 'no-class'}"
                
                if key not in parent_info:
                    parent_info[key] = {
                        'count': 0,
                        'examples': [],
                        'has_price': False,
                        'has_name': False
                    }
                
                parent_info[key]['count'] += 1
                
                # Проверяем есть ли цена в этом элементе
                price_text = current.get_text()
                if re.search(r'\d+[,.]?\d*\s*₽', price_text):
                    parent_info[key]['has_price'] = True
                
                # Проверяем есть ли название товара
                if len(price_text.strip()) > 50:  # Предполагаем что название длинное
                    parent_info[key]['has_name'] = True
                
                # Сохраняем пример
                if len(parent_info[key]['examples']) < 2:
                    article_match = article_pattern.search(current.get_text())
                    if article_match:
                        parent_info[key]['examples'].append(article_match.group())
            
            current = current.parent
            depth += 1
    
    # Сортируем по количеству и показываем лучшие кандидаты
    sorted_parents = sorted(parent_info.items(), key=lambda x: x[1]['count'], reverse=True)
    
    print(f"\n🏆 Лучшие кандидаты для контейнера товара:")
    
    for i, (selector, info) in enumerate(sorted_parents[:5]):
        score = info['count']
        if info['has_price']:
            score += 10
        if info['has_name']:
            score += 5
        
        print(f"{i+1}. {selector}")
        print(f"   📊 Количество: {info['count']}")
        print(f"   💰 Есть цена: {'✅' if info['has_price'] else '❌'}")
        print(f"   📝 Есть название: {'✅' if info['has_name'] else '❌'}")
        print(f"   🏷️ Примеры: {', '.join(info['examples'])}")
        print(f"   ⭐ Оценка: {score}")
        print()

def find_specific_elements(filename):
    """Ищем конкретные элементы для цен и названий"""
    
    if not os.path.exists(filename):
        return
    
    print(f"🔍 Ищем элементы цен и названий в {filename}")
    
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Ищем элементы с ценами
    price_pattern = re.compile(r'\d+[,.]?\d*\s*₽')
    price_elements = []
    
    for element in soup.find_all(text=price_pattern):
        parent = element.parent
        if parent:
            price_elements.append({
                'tag': parent.name,
                'class': parent.get('class', []),
                'id': parent.get('id', ''),
                'text': element.strip(),
                'attributes': dict(parent.attrs)
            })
    
    print(f"💰 Найдено элементов с ценами: {len(price_elements)}")
    
    # Анализируем атрибуты элементов с ценами
    price_attrs = {}
    for elem in price_elements[:10]:
        for attr, value in elem['attributes'].items():
            if attr not in price_attrs:
                price_attrs[attr] = []
            price_attrs[attr].append(str(value))
    
    print(f"📊 Атрибуты элементов с ценами:")
    for attr, values in price_attrs.items():
        unique_values = list(set(values))[:3]  # Первые 3 уникальных значения
        print(f"  {attr}: {', '.join(unique_values)}")

def main():
    """Анализируем HTML файлы"""
    
    html_files = [f for f in os.listdir('.') if f.startswith('debug_search_') and f.endswith('.html')]
    
    if not html_files:
        print("❌ HTML файлы не найдены")
        return
    
    # Анализируем первый файл детально
    first_file = html_files[0]
    
    find_product_structure(first_file)
    print("\n" + "="*60 + "\n")
    find_specific_elements(first_file)

if __name__ == "__main__":
    main()
