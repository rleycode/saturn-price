#!/usr/bin/env python3
"""
Тестовый скрипт для проверки обновления цен в базе данных
"""

import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bitrix_integration import BitrixClient, BitrixConfig

def test_price_update():
    """Тестирование обновления цены одного товара"""
    
    # Конфигурация из .env
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-'),
        underprice_url=os.getenv('SATURN_UNDERPRICE_URL'),
        underprice_password=os.getenv('SATURN_UNDERPRICE_PASSWORD')
    )
    
    print("🔧 Тестирование обновления цен в базе данных...")
    
    with BitrixClient(config) as bitrix:
        # Получаем первый товар Saturn для тестирования
        products = bitrix.get_products_by_prefix()
        if not products:
            print("❌ Товары Saturn не найдены")
            return False
        
        test_product = products[0]
        print(f"📦 Тестовый товар: {test_product.article} (ID: {test_product.id})")
        
        # Получаем текущую цену
        cursor = bitrix.connection.cursor(dictionary=True)
        cursor.execute("""
        SELECT PRICE FROM b_catalog_price 
        WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = 1
        """, (test_product.id,))
        
        current_price_row = cursor.fetchone()
        current_price = float(current_price_row['PRICE']) if current_price_row else 0.0
        
        print(f"💰 Текущая цена: {current_price} руб.")
        
        # Устанавливаем тестовую цену
        test_price = 999.99
        print(f"🔄 Обновляем цену на: {test_price} руб.")
        
        # Обновляем цену
        success = bitrix.update_product_price(test_product.id, test_price)
        
        if success:
            print("✅ Обновление выполнено успешно")
            
            # Проверяем, что цена действительно изменилась
            cursor.execute("""
            SELECT PRICE FROM b_catalog_price 
            WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = 1
            """, (test_product.id,))
            
            updated_price_row = cursor.fetchone()
            updated_price = float(updated_price_row['PRICE']) if updated_price_row else 0.0
            
            print(f"💰 Новая цена в БД: {updated_price} руб.")
            
            if abs(updated_price - test_price) < 0.01:
                print("✅ Цена успешно обновлена в базе данных!")
                
                # Возвращаем исходную цену
                if current_price > 0:
                    bitrix.update_product_price(test_product.id, current_price)
                    print(f"🔄 Восстановлена исходная цена: {current_price} руб.")
                
                return True
            else:
                print(f"❌ Цена в БД не соответствует ожидаемой: {updated_price} != {test_price}")
                return False
        else:
            print("❌ Ошибка обновления цены")
            return False
        
        cursor.close()

if __name__ == "__main__":
    success = test_price_update()
    sys.exit(0 if success else 1)
