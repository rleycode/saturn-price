#!/usr/bin/env python3

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from bitrix_integration import BitrixClient, BitrixConfig
import os
from dotenv import load_dotenv

load_dotenv()

def export_missing_products():
    """Выгружает названия товаров Saturn из базы данных для проверки их существования"""
    
    # Проблемные SKU которые не найдены на сайте
    missing_skus = ["216212", "205897", "190081", "192633", "190080", "145983", "014143", "137742"]
    
    print("📋 ВЫГРУЗКА ДАННЫХ О НЕСУЩЕСТВУЮЩИХ ТОВАРАХ SATURN")
    print("=" * 60)
    print(f"Проверяем {len(missing_skus)} артикулов из базы данных...")
    print()
    
    # Настройка подключения к Bitrix
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', 'localhost'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-'),
        underprice_url=os.getenv('SATURN_UNDERPRICE_URL'),
        underprice_password=os.getenv('SATURN_UNDERPRICE_PASSWORD')
    )
    
    bitrix_client = BitrixClient(config)
    
    try:
        if not bitrix_client.connect():
            print("❌ Не удалось подключиться к базе данных Bitrix")
            return
        
        print("✅ Подключение к базе данных установлено")
        print()
        
        found_products = []
        not_found_in_db = []
        
        for sku in missing_skus:
            article_with_prefix = f"тов-{sku}"
            
            # SQL запрос для поиска товара по артикулу
            query = """
            SELECT 
                e.ID,
                e.NAME,
                e.ACTIVE,
                e.DATE_CREATE,
                e.TIMESTAMP_X,
                pv.VALUE as ARTICLE
            FROM b_iblock_element e
            LEFT JOIN b_iblock_element_property pv ON e.ID = pv.IBLOCK_ELEMENT_ID 
                AND pv.IBLOCK_PROPERTY_ID = 112
            WHERE e.IBLOCK_ID = %s 
                AND pv.VALUE = %s
            """
            
            cursor = bitrix_client.connection.cursor()
            cursor.execute(query, (config.iblock_id, article_with_prefix))
            result = cursor.fetchone()
            
            if result:
                product_id, name, active, date_create, timestamp_x, article = result
                found_products.append({
                    'sku': sku,
                    'article': article,
                    'name': name,
                    'active': 'Да' if active == 'Y' else 'Нет',
                    'created': date_create.strftime('%Y-%m-%d') if date_create else 'Неизвестно',
                    'updated': timestamp_x.strftime('%Y-%m-%d %H:%M') if timestamp_x else 'Неизвестно'
                })
                print(f"✅ {sku} ({article})")
                print(f"   📝 Название: {name}")
                print(f"   🟢 Активен: {'Да' if active == 'Y' else 'Нет'}")
                print(f"   📅 Создан: {date_create.strftime('%Y-%m-%d') if date_create else 'Неизвестно'}")
                print(f"   🔄 Обновлен: {timestamp_x.strftime('%Y-%m-%d %H:%M') if timestamp_x else 'Неизвестно'}")
            else:
                not_found_in_db.append(sku)
                print(f"❌ {sku} - НЕ НАЙДЕН в базе данных")
            
            print()
        
        # Сохраняем результаты в CSV файл
        import csv
        with open('missing_saturn_products.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['sku', 'article', 'name', 'active', 'created', 'updated', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for product in found_products:
                product['status'] = 'Найден в БД, не найден на сайте'
                writer.writerow(product)
            
            for sku in not_found_in_db:
                writer.writerow({
                    'sku': sku,
                    'article': f'тов-{sku}',
                    'name': 'НЕ НАЙДЕН В БАЗЕ ДАННЫХ',
                    'active': '',
                    'created': '',
                    'updated': '',
                    'status': 'Отсутствует в БД'
                })
        
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 30)
        print(f"Всего проверено артикулов: {len(missing_skus)}")
        print(f"Найдено в базе данных: {len(found_products)}")
        print(f"Не найдено в базе данных: {len(not_found_in_db)}")
        print()
        print("💾 Результаты сохранены в файл: missing_saturn_products.csv")
        print()
        
        if found_products:
            print("🔍 ТОВАРЫ ДЛЯ ПРОВЕРКИ НА САЙТЕ SATURN:")
            print("-" * 40)
            for product in found_products:
                print(f"• {product['sku']}: {product['name']}")
        
        if not_found_in_db:
            print("⚠️  АРТИКУЛЫ НЕ НАЙДЕНЫ В БАЗЕ ДАННЫХ:")
            print("-" * 40)
            for sku in not_found_in_db:
                print(f"• {sku}")
    
    except Exception as e:
        print(f"💥 Ошибка: {e}")
    
    finally:
        bitrix_client.disconnect()

if __name__ == "__main__":
    export_missing_products()
