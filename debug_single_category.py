#!/usr/bin/env python3
"""
Детальная диагностика одной страницы категории Saturn
"""

import requests
from bs4 import BeautifulSoup
import re

def analyze_single_category():
    """Анализируем одну категорию детально"""
    
    # Берем первую категорию из диагностики
    url = "https://nnv.saturn.net/catalog/brusok-rejka/tag-50-mm/"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    print(f"🔍 ДЕТАЛЬНЫЙ АНАЛИЗ: {url}")
    print("=" * 60)
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем контейнеры товаров
        containers = soup.select('div.h_s_list_categor_item_wrap')
        print(f"📦 Найдено контейнеров: {len(containers)}")
        
        if containers:
            # Анализируем первые 3 контейнера
            for i, container in enumerate(containers[:3], 1):
                print(f"\n--- КОНТЕЙНЕР {i} ---")
                
                # Показываем HTML структуру контейнера
                print("HTML структура:")
                print(str(container)[:500] + "..." if len(str(container)) > 500 else str(container))
                
                # Ищем артикул разными способами
                print(f"\n🏷️  ПОИСК АРТИКУЛА:")
                
                # Способ 1: p.h_s_list_categor_item_articul
                article_elem = container.select_one('p.h_s_list_categor_item_articul')
                if article_elem:
                    print(f"   ✅ p.h_s_list_categor_item_articul: '{article_elem.get_text(strip=True)}'")
                else:
                    print(f"   ❌ p.h_s_list_categor_item_articul: не найден")
                
                # Способ 2: все p элементы
                p_elements = container.find_all('p')
                print(f"   📄 Всего p элементов: {len(p_elements)}")
                for j, p in enumerate(p_elements):
                    p_text = p.get_text(strip=True)
                    p_classes = p.get('class', [])
                    print(f"      p[{j}]: class='{p_classes}' text='{p_text}'")
                
                # Способ 3: поиск тов- в тексте контейнера
                container_text = container.get_text()
                article_matches = re.findall(r'тов-(\d+)', container_text, re.IGNORECASE)
                if article_matches:
                    print(f"   ✅ Артикулы в тексте: {article_matches}")
                else:
                    print(f"   ❌ Артикулы в тексте: не найдены")
                
                # Ищем цену
                print(f"\n💰 ПОИСК ЦЕНЫ:")
                
                # Способ 1: span.shopping_cart_goods_list_item_sum_item
                price_elem = container.select_one('span.shopping_cart_goods_list_item_sum_item')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    data_price = price_elem.get('data-price')
                    print(f"   ✅ span.shopping_cart_goods_list_item_sum_item: text='{price_text}' data-price='{data_price}'")
                else:
                    print(f"   ❌ span.shopping_cart_goods_list_item_sum_item: не найден")
                
                # Способ 2: все span элементы
                span_elements = container.find_all('span')
                print(f"   📄 Всего span элементов: {len(span_elements)}")
                for j, span in enumerate(span_elements[:5]):  # Показываем только первые 5
                    span_text = span.get_text(strip=True)
                    span_classes = span.get('class', [])
                    data_price = span.get('data-price')
                    print(f"      span[{j}]: class='{span_classes}' text='{span_text}' data-price='{data_price}'")
                
                # Способ 3: поиск цен в тексте
                price_matches = re.findall(r'(\d+[,.]?\d*)\s*₽', container_text)
                if price_matches:
                    print(f"   ✅ Цены в тексте: {price_matches}")
                else:
                    print(f"   ❌ Цены в тексте: не найдены")
                
                # Ищем название товара
                print(f"\n📝 ПОИСК НАЗВАНИЯ:")
                
                # Способ 1: a.h_s_list_categor_item
                name_elem = container.select_one('a.h_s_list_categor_item')
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    href = name_elem.get('href')
                    print(f"   ✅ a.h_s_list_categor_item: '{name_text}' href='{href}'")
                else:
                    print(f"   ❌ a.h_s_list_categor_item: не найден")
                
                # Способ 2: все a элементы
                a_elements = container.find_all('a')
                print(f"   📄 Всего a элементов: {len(a_elements)}")
                for j, a in enumerate(a_elements[:3]):  # Показываем только первые 3
                    a_text = a.get_text(strip=True)
                    a_classes = a.get('class', [])
                    href = a.get('href')
                    print(f"      a[{j}]: class='{a_classes}' text='{a_text[:50]}...' href='{href}'")
        
        # Сохраняем полный HTML для анализа
        with open('debug_single_category.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n💾 Полный HTML сохранен: debug_single_category.html")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    analyze_single_category()
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
