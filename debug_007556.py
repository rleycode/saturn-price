#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import re
import time

def debug_product_007556():
    """Отладка поиска товара 007556 на Saturn"""
    
    sku = "007556"
    article_with_prefix = f"тов-{sku}"
    
    print(f"🔍 ОТЛАДКА ПОИСКА ТОВАРА {article_with_prefix}")
    print("=" * 50)
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    # МЕТОД 1: Поиск в контейнерах товаров
    print("\n📦 МЕТОД 1: Поиск в контейнерах товаров")
    print("-" * 30)
    
    search_url = f"https://saturn-r.ru/search/?q={sku}"
    print(f"URL поиска: {search_url}")
    
    try:
        response = session.get(search_url, timeout=10)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем контейнеры товаров
            product_containers = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            print(f"Найдено контейнеров товаров: {len(product_containers)}")
            
            for i, container in enumerate(product_containers[:5]):  # Показываем первые 5
                article_elem = container.find('p', class_='h_s_list_categor_item_articul')
                name_elem = container.find('a', class_='h_s_list_categor_item')
                
                if article_elem and name_elem:
                    found_article = article_elem.get_text(strip=True)
                    found_name = name_elem.get_text(strip=True)
                    print(f"  {i+1}. {found_article}: {found_name}")
                    
                    if found_article == article_with_prefix:
                        print(f"  ✅ НАЙДЕН! {found_article}")
                        return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Ошибка Метода 1: {e}")
    
    # МЕТОД 2: Поиск по ссылкам на товары
    print("\n🔗 МЕТОД 2: Поиск по ссылкам на товары")
    print("-" * 30)
    
    try:
        response = session.get(search_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем ссылки на товары
            product_links = soup.find_all('a', href=re.compile(r'/catalog/[^/]+/[^/]+/$'))
            print(f"Найдено ссылок на товары: {len(product_links)}")
            
            for i, link in enumerate(product_links[:3]):  # Проверяем первые 3
                product_url = "https://saturn-r.ru" + link['href']
                print(f"  {i+1}. Проверяем: {product_url}")
                
                try:
                    product_response = session.get(product_url, timeout=10)
                    if product_response.status_code == 200:
                        product_soup = BeautifulSoup(product_response.content, 'html.parser')
                        
                        # Ищем артикул на странице товара
                        article_patterns = [
                            r'тов-\d{6}',
                            r'Артикул[:\s]*тов-\d{6}',
                            r'Код товара[:\s]*тов-\d{6}'
                        ]
                        
                        page_text = product_soup.get_text()
                        for pattern in article_patterns:
                            matches = re.findall(pattern, page_text, re.IGNORECASE)
                            if matches:
                                found_article = matches[0].replace('Артикул:', '').replace('Код товара:', '').strip()
                                print(f"    Найден артикул: {found_article}")
                                
                                if found_article == article_with_prefix:
                                    print(f"    ✅ НАЙДЕН! {found_article}")
                                    return True
                    
                    time.sleep(0.5)  # Пауза между запросами
                
                except Exception as e:
                    print(f"    ❌ Ошибка при проверке товара: {e}")
    
    except Exception as e:
        print(f"❌ Ошибка Метода 2: {e}")
    
    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Прямой поиск по артикулу
    print(f"\n🎯 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Поиск по полному артикулу")
    print("-" * 30)
    
    full_search_url = f"https://saturn-r.ru/search/?q={article_with_prefix}"
    print(f"URL поиска: {full_search_url}")
    
    try:
        response = session.get(full_search_url, timeout=10)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            product_containers = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            print(f"Найдено контейнеров товаров: {len(product_containers)}")
            
            for i, container in enumerate(product_containers):
                article_elem = container.find('p', class_='h_s_list_categor_item_articul')
                name_elem = container.find('a', class_='h_s_list_categor_item')
                
                if article_elem and name_elem:
                    found_article = article_elem.get_text(strip=True)
                    found_name = name_elem.get_text(strip=True)
                    print(f"  {i+1}. {found_article}: {found_name}")
                    
                    if found_article == article_with_prefix:
                        print(f"  ✅ НАЙДЕН! {found_article}")
                        return True
    
    except Exception as e:
        print(f"❌ Ошибка дополнительной проверки: {e}")
    
    print(f"\n❌ ТОВАР {article_with_prefix} НЕ НАЙДЕН НИКАКИМ МЕТОДОМ")
    return False

if __name__ == "__main__":
    debug_product_007556()
