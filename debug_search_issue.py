#!/usr/bin/env python3
"""
Диагностика проблемы поиска товаров Saturn
"""

import requests
from bs4 import BeautifulSoup
import time

def test_search_methods(sku: str):
    """Тестируем разные методы поиска товара"""
    
    print(f"🔍 Тестируем поиск товара: {sku}")
    
    # Разные варианты URL поиска
    search_urls = [
        f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s=тов-{sku}",
        f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={sku}",
        f"https://nnv.saturn.net/catalog/?search=тов-{sku}",
        f"https://nnv.saturn.net/catalog/?search={sku}",
        f"https://nnv.saturn.net/search/?q=тов-{sku}",
        f"https://nnv.saturn.net/search/?q={sku}"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for i, url in enumerate(search_urls, 1):
        print(f"\n📍 Метод {i}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем товары с новыми селекторами
            product_items = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            print(f"  📦 Найдено товаров: {len(product_items)}")
            
            # Ищем конкретный артикул
            found_target = False
            for item in product_items:
                article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                if article_elem:
                    article_text = article_elem.get_text(strip=True)
                    if f"тов-{sku}" in article_text:
                        found_target = True
                        print(f"  ✅ НАЙДЕН целевой товар: {article_text}")
                        
                        # Извлекаем цену
                        price_elem = item.find('span', class_='shopping_cart_goods_list_item_sum_item')
                        if price_elem:
                            price_text = price_elem.get_text(strip=True)
                            print(f"  💰 Цена: {price_text}")
                        else:
                            # Альтернативный поиск цены
                            import re
                            item_text = item.get_text()
                            price_match = re.search(r'(\d+[,.]?\d*)\s*₽', item_text)
                            if price_match:
                                print(f"  💰 Цена (regex): {price_match.group(0)}")
                        break
            
            if not found_target and product_items:
                print(f"  ❌ Целевой товар НЕ найден среди {len(product_items)} товаров")
                # Показываем первые несколько артикулов для анализа
                for j, item in enumerate(product_items[:3]):
                    article_elem = item.find('p', class_='h_s_list_categor_item_articul')
                    if article_elem:
                        article_text = article_elem.get_text(strip=True)
                        print(f"    {j+1}. {article_text}")
            elif not product_items:
                print(f"  ❌ Товары не найдены")
                
                # Проверяем есть ли сообщение об отсутствии результатов
                page_text = soup.get_text().lower()
                if any(phrase in page_text for phrase in ['не найдено', 'ничего не найдено', 'нет результатов']):
                    print(f"  📄 Страница содержит сообщение об отсутствии результатов")
                else:
                    print(f"  📄 Размер страницы: {len(response.content)} байт")
            
            if found_target:
                print(f"  🎉 УСПЕХ! Товар найден методом {i}")
                return True
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        
        time.sleep(1)  # Пауза между запросами
    
    return False

def test_multiple_skus():
    """Тестируем несколько SKU для выявления паттерна"""
    
    # SKU которые не найдены из логов
    failed_skus = ["014143", "137742", "007476", "058173", "007554"]
    # SKU которые найдены из логов
    success_skus = ["089749", "040688"]
    
    print("="*60)
    print("🔍 ТЕСТИРУЕМ НЕ НАЙДЕННЫЕ SKU:")
    print("="*60)
    
    for sku in failed_skus[:2]:  # Тестируем только первые 2
        result = test_search_methods(sku)
        if result:
            print(f"✅ {sku} - найден альтернативным методом")
        else:
            print(f"❌ {sku} - не найден ни одним методом")
        print("-" * 40)
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРУЕМ НАЙДЕННЫЕ SKU:")
    print("="*60)
    
    for sku in success_skus[:1]:  # Тестируем только первый
        result = test_search_methods(sku)
        if result:
            print(f"✅ {sku} - подтверждено")
        else:
            print(f"❌ {sku} - неожиданно не найден")
        print("-" * 40)

if __name__ == "__main__":
    test_multiple_skus()
