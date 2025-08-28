#!/usr/bin/env python3
"""
Проверка цен в базе данных Bitrix
Анализ структуры таблицы b_catalog_price и актуальных цен
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Загрузка переменных окружения
load_dotenv()

def check_price_structure():
    """Проверка структуры цен в базе данных"""
    
    # Подключение к MySQL
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
    
    print("🔍 Анализ структуры цен в Bitrix...")
    
    # 1. Проверяем группы цен
    print("\n📊 Группы цен (CATALOG_GROUP):")
    cursor.execute("""
    SELECT ID, NAME, BASE, SORT 
    FROM b_catalog_group 
    ORDER BY SORT, ID
    """)
    
    groups = cursor.fetchall()
    for group in groups:
        print(f"  ID {group['ID']}: {group['NAME']} (BASE: {group['BASE']})")
    
    # 2. Проверяем цены для тестового товара
    supplier_prefix = os.getenv('SUPPLIER_PREFIX', 'тов-')
    print(f"\n💰 Цены для товаров с префиксом '{supplier_prefix}':")
    
    cursor.execute("""
    SELECT 
        e.ID as PRODUCT_ID,
        prop.VALUE as ARTICLE,
        e.NAME,
        price.CATALOG_GROUP_ID,
        cg.NAME as GROUP_NAME,
        price.PRICE,
        price.TIMESTAMP_X
    FROM b_iblock_element e
    LEFT JOIN b_iblock_element_property prop ON (
        e.ID = prop.IBLOCK_ELEMENT_ID 
        AND prop.IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
        )
    )
    LEFT JOIN b_catalog_price price ON e.ID = price.PRODUCT_ID
    LEFT JOIN b_catalog_group cg ON price.CATALOG_GROUP_ID = cg.ID
    WHERE e.ACTIVE = 'Y' 
    AND prop.VALUE LIKE %s
    AND price.PRICE IS NOT NULL
    ORDER BY e.ID, price.CATALOG_GROUP_ID
    LIMIT 20
    """, (f"{supplier_prefix}%",))
    
    prices = cursor.fetchall()
    current_product = None
    
    for price in prices:
        if current_product != price['PRODUCT_ID']:
            current_product = price['PRODUCT_ID']
            print(f"\n📦 {price['ARTICLE']} (ID: {price['PRODUCT_ID']}):")
        
        print(f"  Группа {price['CATALOG_GROUP_ID']} ({price['GROUP_NAME']}): {price['PRICE']} руб. ({price['TIMESTAMP_X']})")
    
    # 3. Проверяем последние обновления цен
    print(f"\n🕐 Последние обновления цен для Saturn товаров:")
    cursor.execute("""
    SELECT 
        e.ID as PRODUCT_ID,
        prop.VALUE as ARTICLE,
        price.CATALOG_GROUP_ID,
        cg.NAME as GROUP_NAME,
        price.PRICE,
        price.TIMESTAMP_X
    FROM b_iblock_element e
    LEFT JOIN b_iblock_element_property prop ON (
        e.ID = prop.IBLOCK_ELEMENT_ID 
        AND prop.IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
        )
    )
    LEFT JOIN b_catalog_price price ON e.ID = price.PRODUCT_ID
    LEFT JOIN b_catalog_group cg ON price.CATALOG_GROUP_ID = cg.ID
    WHERE e.ACTIVE = 'Y' 
    AND prop.VALUE LIKE %s
    AND price.PRICE IS NOT NULL
    AND price.TIMESTAMP_X >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
    ORDER BY price.TIMESTAMP_X DESC
    LIMIT 10
    """, (f"{supplier_prefix}%",))
    
    recent_updates = cursor.fetchall()
    if recent_updates:
        for update in recent_updates:
            print(f"  {update['ARTICLE']} - Группа {update['CATALOG_GROUP_ID']}: {update['PRICE']} руб. ({update['TIMESTAMP_X']})")
    else:
        print("  Нет обновлений за последний час")
    
    # 4. Статистика по группам цен
    print(f"\n📈 Статистика цен по группам для Saturn товаров:")
    cursor.execute("""
    SELECT 
        price.CATALOG_GROUP_ID,
        cg.NAME as GROUP_NAME,
        COUNT(*) as PRODUCTS_COUNT,
        AVG(price.PRICE) as AVG_PRICE,
        MIN(price.PRICE) as MIN_PRICE,
        MAX(price.PRICE) as MAX_PRICE
    FROM b_iblock_element e
    LEFT JOIN b_iblock_element_property prop ON (
        e.ID = prop.IBLOCK_ELEMENT_ID 
        AND prop.IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
        )
    )
    LEFT JOIN b_catalog_price price ON e.ID = price.PRODUCT_ID
    LEFT JOIN b_catalog_group cg ON price.CATALOG_GROUP_ID = cg.ID
    WHERE e.ACTIVE = 'Y' 
    AND prop.VALUE LIKE %s
    AND price.PRICE IS NOT NULL
    GROUP BY price.CATALOG_GROUP_ID, cg.NAME
    ORDER BY price.CATALOG_GROUP_ID
    """, (f"{supplier_prefix}%",))
    
    stats = cursor.fetchall()
    for stat in stats:
        print(f"  Группа {stat['CATALOG_GROUP_ID']} ({stat['GROUP_NAME']}): {stat['PRODUCTS_COUNT']} товаров, средняя цена: {stat['AVG_PRICE']:.2f} руб.")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    try:
        check_price_structure()
    except Error as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
