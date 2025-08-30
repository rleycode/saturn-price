#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def test_new_saturn_url():
    """Тестируем новый правильный URL поиска Saturn"""
    
    sku = "007556"
    # Используем правильный URL из примера пользователя
    search_url = f"https://nnv.saturn.net/catalog/?sp%5Bname%5D=1&sp%5Bartikul%5D=1&search=&s={sku}"
    
    print(f"🔍 ТЕСТ НОВОГО URL ПОИСКА SATURN")
    print("=" * 50)
    print(f"SKU: {sku}")
    print(f"URL: {search_url}")
    print()
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    try:
        response = session.get(search_url, timeout=15)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем контейнеры товаров
            product_containers = soup.find_all('div', class_='h_s_list_categor_item_wrap')
            print(f"Найдено контейнеров товаров: {len(product_containers)}")
            
            if len(product_containers) == 0:
                # Попробуем найти другие возможные контейнеры
                print("\nПоиск альтернативных контейнеров...")
                all_divs = soup.find_all('div', class_=True)
                for div in all_divs[:10]:
                    classes = ' '.join(div.get('class', []))
                    if 'item' in classes.lower() or 'product' in classes.lower() or 'catalog' in classes.lower():
                        print(f"  Найден div с классом: {classes}")
            
            found_product = False
            expected_article = f"тов-{sku}"
            
            for i, container in enumerate(product_containers):
                # Ищем артикул
                article_elem = container.find('p', class_='h_s_list_categor_item_articul')
                if not article_elem:
                    # Попробуем альтернативные селекторы
                    article_elem = container.find('span', class_='article')
                    if not article_elem:
                        article_elem = container.find(string=lambda text: text and 'тов-' in text)
                
                # Ищем название
                name_elem = container.find('a', class_='h_s_list_categor_item')
                if not name_elem:
                    name_elem = container.find('a', class_='name')
                
                # Ищем цену
                price_elem = container.find('span', class_='js-price-value')
                if not price_elem:
                    price_elem = container.find('span', attrs={'data-price': True})
                
                if article_elem:
                    article_text = article_elem.get_text(strip=True) if hasattr(article_elem, 'get_text') else str(article_elem).strip()
                    name_text = name_elem.get_text(strip=True) if name_elem else "Название не найдено"
                    
                    price_text = "Цена не найдена"
                    if price_elem:
                        if price_elem.get('data-price'):
                            price_text = f"{price_elem.get('data-price')} руб."
                        else:
                            price_text = price_elem.get_text(strip=True)
                    
                    print(f"\n  Товар {i+1}:")
                    print(f"    Артикул: {article_text}")
                    print(f"    Название: {name_text}")
                    print(f"    Цена: {price_text}")
                    
                    if expected_article in article_text:
                        print(f"    ✅ НАЙДЕН ИСКОМЫЙ ТОВАР!")
                        found_product = True
            
            if not found_product:
                print(f"\n❌ Товар {expected_article} не найден среди результатов")
                
                # Проверим весь текст страницы на наличие артикула
                page_text = soup.get_text()
                if expected_article in page_text:
                    print(f"✅ Но артикул {expected_article} присутствует в тексте страницы")
                else:
                    print(f"❌ Артикул {expected_article} отсутствует в тексте страницы")
            else:
                print(f"\n🎉 УСПЕХ! Товар найден с новым URL!")
        
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(f"Текст ответа: {response.text[:500]}...")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_new_saturn_url()
