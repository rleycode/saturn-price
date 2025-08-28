#!/usr/bin/env python3
"""
Тест основного метода синхронизации
"""

import os
from bitrix_integration import BitrixClient, BitrixConfig
from dotenv import load_dotenv

def test_sync():
    """Тест получения товаров через основной метод"""
    
    # Загружаем .env файл
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    
    # Конфигурация
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', 'localhost'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    print(f"🔍 Тестируем получение товаров с префиксом: '{config.supplier_prefix}'")
    print("-" * 60)
    
    with BitrixClient(config) as bitrix:
        # Используем основной метод
        products = bitrix.get_products_by_prefix()
        
        print(f"📊 Найдено товаров: {len(products)}")
        
        if products:
            print("\n📦 Первые 5 товаров:")
            for i, product in enumerate(products[:5]):
                print(f"  {i+1}. ID: {product.id}, Артикул: {product.article}, Название: {product.name[:50]}...")
        else:
            print("❌ Товары не найдены!")
            
            # Дополнительная диагностика
            cursor = bitrix.connection.cursor(dictionary=True)
            
            # Проверим, есть ли поле CML2_ARTICLE
            cursor.execute("""
            SELECT ID, CODE, NAME 
            FROM b_iblock_property 
            WHERE IBLOCK_ID = %s AND CODE = 'CML2_ARTICLE'
            """, (config.iblock_id,))
            
            prop_result = cursor.fetchone()
            if prop_result:
                print(f"✅ Поле CML2_ARTICLE найдено: ID={prop_result['ID']}")
                
                # Проверим, есть ли значения в этом поле с нашим префиксом
                cursor.execute("""
                SELECT COUNT(*) as count
                FROM b_iblock_element_property p
                WHERE p.IBLOCK_PROPERTY_ID = %s
                AND p.VALUE LIKE %s
                """, (prop_result['ID'], f"{config.supplier_prefix}%"))
                
                count_result = cursor.fetchone()
                print(f"📊 Значений с префиксом '{config.supplier_prefix}': {count_result['count']}")
                
                # Проверим активные элементы с этим префиксом
                cursor.execute("""
                SELECT COUNT(*) as count
                FROM b_iblock_element e
                JOIN b_iblock_element_property p ON e.ID = p.IBLOCK_ELEMENT_ID
                WHERE e.IBLOCK_ID = %s 
                AND e.ACTIVE = 'Y'
                AND p.IBLOCK_PROPERTY_ID = %s
                AND p.VALUE LIKE %s
                """, (config.iblock_id, prop_result['ID'], f"{config.supplier_prefix}%"))
                
                active_count = cursor.fetchone()
                print(f"📊 Активных товаров с префиксом: {active_count['count']}")
            else:
                print("❌ Поле CML2_ARTICLE не найдено!")
            
            cursor.close()

if __name__ == "__main__":
    test_sync()
