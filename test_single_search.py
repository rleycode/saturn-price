#!/usr/bin/env python3
"""
Тестовый скрипт для проверки поиска одного товара на Saturn
"""

import requests
from bs4 import BeautifulSoup
import time

def test_saturn_search(sku: str):
    """Тестируем поиск конкретного товара"""
    
    # URL поиска Saturn
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s=тов-{sku}"
    
    print(f"🔍 Тестируем поиск товара: тов-{sku}")
    print(f"📍 URL: {search_url}")
    
    try:
        # Делаем запрос
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"✅ HTTP статус: {response.status_code}")
        print(f"📄 Размер ответа: {len(response.content)} байт")
        
        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем товары с новыми селекторами
        product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
        print(f"🛍️ Найдено элементов h_s_list_categor_item_wrap: {len(product_items)}")
        
        # Также проверяем старые селекторы для сравнения
        old_items = soup.find_all('div', class_='catalog-item')
        print(f"📦 Найдено элементов catalog-item (старый): {len(old_items)}")
        
        if not product_items:
            # Проверяем другие возможные классы
            all_divs = soup.find_all('div')
            print(f"📊 Всего div элементов: {len(all_divs)}")
            
            # Ищем элементы с артикулами в новых селекторах
            article_elems = soup.find_all('p', class_='h_s_list_categor_item_articul')
            print(f"🏷️ Найдено p.h_s_list_categor_item_articul: {len(article_elems)}")
            
            # Ищем любые элементы с текстом 'тов-'
            all_with_tov = soup.find_all(string=lambda text: text and 'тов-' in text.lower())
            print(f"🔍 Найдено любых элементов с 'тов-': {len(all_with_tov)}")
            
            for elem in article_elems[:5]:  # Показываем первые 5
                print(f"  - {elem.get_text(strip=True)}")
            
            # Показываем примеры текста с 'тов-'
            for text in all_with_tov[:5]:
                if text.strip():
                    print(f"  📄 Текст: {text.strip()}")
            
            # Сохраняем HTML для анализа
            with open(f"debug_search_{sku}.html", "w", encoding='utf-8') as f:
                f.write(response.text)
            print(f"💾 HTML сохранен в debug_search_{sku}.html")
            
            return False
        
        # Анализируем найденные товары
        found_target = False
        for i, item in enumerate(product_items):
            print(f"\n📦 Товар #{i+1}:")
            
            # Ищем артикул с новым селектором
            article_elem = item.find('p', class_='h_s_list_categor_item_articul')
            if article_elem:
                article_text = article_elem.get_text(strip=True)
                print(f"  🏷️ Артикул: {article_text}")
                
                if f"тов-{sku}" in article_text:
                    found_target = True
                    print(f"  ✅ НАЙДЕН целевой товар!")
            
            # Ищем название с новым селектором
            name_elem = item.find('a', class_='h_s_list_categor_item')
            if name_elem:
                name = name_elem.get_text(strip=True)
                print(f"  📝 Название: {name}")
            
            # Ищем цену с новым селектором
            price_elem = item.find('span', class_='shopping_cart_goods_list_item_sum_item')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                print(f"  💰 Цена: {price_text}")
            else:
                # Ищем цену в тексте товара
                import re
                item_text = item.get_text()
                price_match = re.search(r'(\d+[,.]?\d*)\s*₽', item_text)
                if price_match:
                    print(f"  💰 Цена (regex): {price_match.group(0)}")
                else:
                    print(f"  ❌ Цена не найдена")
        
        if found_target:
            print(f"\n🎉 Товар тов-{sku} НАЙДЕН на сайте!")
            return True
        else:
            print(f"\n❌ Товар тов-{sku} НЕ НАЙДЕН среди результатов")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    # Тестируем несколько артикулов из логов
    test_skus = ["103516", "114289", "114290", "138859", "037103"]
    
    for sku in test_skus:
        print("="*60)
        result = test_saturn_search(sku)
        time.sleep(2)  # Пауза между запросами
        
        if result:
            break  # Если нашли хотя бы один, останавливаемся
