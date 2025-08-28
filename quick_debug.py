#!/usr/bin/env python3
"""
Быстрая диагностика групп цен
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def quick_debug():
    connection = mysql.connector.connect(
        host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        user=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        charset='utf8mb4',
        use_pure=True
    )
    
    cursor = connection.cursor(dictionary=True)
    
    print("🔍 Быстрая диагностика...")
    
    # 1. Проверяем структуру таблицы групп цен
    print("\n📊 Структура таблицы b_catalog_group:")
    cursor.execute("DESCRIBE b_catalog_group")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['Field']}: {col['Type']}")
    
    # 2. Проверяем группы цен
    print("\n💰 Группы цен:")
    cursor.execute("SELECT ID, NAME, BASE, SORT FROM b_catalog_group ORDER BY SORT, ID")
    groups = cursor.fetchall()
    for group in groups:
        base_mark = "🔥 БАЗОВАЯ" if group['BASE'] == 'Y' else ""
        print(f"  ID {group['ID']}: {group['NAME']} {base_mark}")
    
    # 3. Проверяем тестовый товар Saturn
    supplier_prefix = os.getenv('SUPPLIER_PREFIX', 'тов-')
    print(f"\n🧪 Тестовый товар Saturn (префикс: {supplier_prefix}):")
    
    cursor.execute("""
    SELECT 
        e.ID,
        e.NAME,
        e.ACTIVE,
        prop.VALUE as ARTICLE
    FROM b_iblock_element e
    LEFT JOIN b_iblock_element_property prop ON (
        e.ID = prop.IBLOCK_ELEMENT_ID 
        AND prop.IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
        )
    )
    WHERE e.ACTIVE = 'Y' 
    AND e.IBLOCK_ID = %s
    AND prop.VALUE LIKE %s
    ORDER BY e.ID
    LIMIT 1
    """, (int(os.getenv('BITRIX_IBLOCK_ID', 11)), f"{supplier_prefix}%"))
    
    test_product = cursor.fetchone()
    if test_product:
        print(f"  📦 {test_product['ARTICLE']} (ID: {test_product['ID']})")
        print(f"    Название: {test_product['NAME']}")
        print(f"    Активен: {test_product['ACTIVE']}")
        
        # Проверяем цены этого товара
        cursor.execute("""
        SELECT 
            price.CATALOG_GROUP_ID,
            cg.NAME as GROUP_NAME,
            price.PRICE,
            price.TIMESTAMP_X
        FROM b_catalog_price price
        LEFT JOIN b_catalog_group cg ON price.CATALOG_GROUP_ID = cg.ID
        WHERE price.PRODUCT_ID = %s
        ORDER BY price.CATALOG_GROUP_ID
        """, (test_product['ID'],))
        
        prices = cursor.fetchall()
        if prices:
            print(f"    Цены:")
            for price in prices:
                print(f"      Группа {price['CATALOG_GROUP_ID']} ({price['GROUP_NAME']}): {price['PRICE']} руб.")
                print(f"        Обновлено: {price['TIMESTAMP_X']}")
        else:
            print("    ❌ Цены не найдены!")
    else:
        print("  ❌ Товары Saturn не найдены!")
    
    # 4. Проверяем общую статистику цен
    print(f"\n📈 Статистика цен:")
    cursor.execute("""
    SELECT 
        cg.ID,
        cg.NAME,
        COUNT(cp.PRODUCT_ID) as PRODUCTS_COUNT
    FROM b_catalog_group cg
    LEFT JOIN b_catalog_price cp ON cg.ID = cp.CATALOG_GROUP_ID
    GROUP BY cg.ID, cg.NAME
    ORDER BY cg.ID
    """)
    
    stats = cursor.fetchall()
    for stat in stats:
        print(f"  Группа {stat['ID']} ({stat['NAME']}): {stat['PRODUCTS_COUNT']} товаров")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    try:
        quick_debug()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
