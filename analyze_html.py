#!/usr/bin/env python3
"""
Анализ HTML страницы Saturn для поиска правильных селекторов товаров
"""

from bs4 import BeautifulSoup
import re

def analyze_saturn_html(filename):
    """Анализ HTML файла Saturn"""
    
    print(f"🔍 Анализируем файл: {filename}")
    print("=" * 60)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html = f.read()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Ищем все ссылки, содержащие артикул
        print("1️⃣ Ссылки, содержащие артикул 103516:")
        all_links = soup.find_all('a', href=True)
        relevant_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '103516' in href or '103516' in text:
                relevant_links.append((href, text[:100]))
        
        for href, text in relevant_links[:10]:  # Показываем первые 10
            print(f"   - {href} | {text}")
        
        # 2. Ищем товарные блоки по классам
        print(f"\n2️⃣ Поиск товарных блоков:")
        
        # Различные селекторы товаров
        selectors = [
            '.product',
            '.item',
            '.goods',
            '.card',
            '[data-product]',
            '[data-item]',
            '.catalog-item',
            '.product-card',
            '.item-card'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"   ✅ {selector}: найдено {len(elements)} элементов")
                
                # Проверяем первый элемент
                first = elements[0]
                if '103516' in str(first):
                    print(f"      🎯 Содержит артикул 103516!")
                    
                    # Ищем ссылку внутри
                    link = first.find('a', href=True)
                    if link:
                        print(f"      🔗 Ссылка: {link.get('href')}")
            else:
                print(f"   ❌ {selector}: не найдено")
        
        # 3. Ищем по тексту "103516"
        print(f"\n3️⃣ Контекст вокруг артикула 103516:")
        
        # Находим все вхождения артикула
        text_content = soup.get_text()
        positions = []
        start = 0
        while True:
            pos = text_content.find('103516', start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        print(f"   Найдено вхождений: {len(positions)}")
        
        for i, pos in enumerate(positions[:3]):  # Показываем первые 3
            context_start = max(0, pos - 100)
            context_end = min(len(text_content), pos + 100)
            context = text_content[context_start:context_end].strip()
            print(f"   {i+1}. ...{context}...")
        
        # 4. Ищем структуру каталога
        print(f"\n4️⃣ Анализ структуры каталога:")
        
        # Ищем формы поиска
        forms = soup.find_all('form')
        print(f"   Форм на странице: {len(forms)}")
        
        for i, form in enumerate(forms[:3]):
            action = form.get('action', 'не указано')
            method = form.get('method', 'GET')
            print(f"   Форма {i+1}: {method} {action}")
            
            # Ищем поля поиска
            inputs = form.find_all('input')
            for inp in inputs:
                name = inp.get('name', '')
                value = inp.get('value', '')
                if name and ('search' in name.lower() or 's' == name):
                    print(f"      Поле поиска: {name} = {value}")
        
        # 5. Поиск JSON данных
        print(f"\n5️⃣ Поиск JSON данных:")
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and '103516' in script.string:
                content = script.string[:200] + "..." if len(script.string) > 200 else script.string
                print(f"   🎯 JSON с артикулом: {content}")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")

if __name__ == "__main__":
    analyze_saturn_html("saturn_search_103516_1.html")
