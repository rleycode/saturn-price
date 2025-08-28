#!/usr/bin/env python3
"""
Диагностика отображения цен в интерфейсе Bitrix
Проверка настроек каталога и групп цен
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Загрузка переменных окружения
load_dotenv()

def debug_bitrix_catalog():
    """Диагностика настроек каталога Bitrix"""
    
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
    
    print("🔍 Диагностика настроек каталога Bitrix...")
    
    # 1. Проверяем настройки информационного блока каталога
    iblock_id = int(os.getenv('BITRIX_IBLOCK_ID', 11))
    print(f"\n📋 Информационный блок каталога (ID: {iblock_id}):")
    
    cursor.execute("""
    SELECT ID, NAME, ACTIVE, LIST_PAGE_URL, DETAIL_PAGE_URL 
    FROM b_iblock 
    WHERE ID = %s
    """, (iblock_id,))
    
    iblock = cursor.fetchone()
    if iblock:
        print(f"  Название: {iblock['NAME']}")
        print(f"  Активен: {iblock['ACTIVE']}")
        print(f"  URL списка: {iblock['LIST_PAGE_URL']}")
        print(f"  URL детали: {iblock['DETAIL_PAGE_URL']}")
    else:
        print("  ❌ Информационный блок не найден!")
        return
    
    # 2. Проверяем привязку каталога к информационному блоку
    print(f"\n🛒 Настройки каталога:")
    cursor.execute("""
    SELECT IBLOCK_ID, YANDEX_EXPORT, SUBSCRIPTION, VAT_ID, 
           PRODUCT_IBLOCK_ID, SKU_PROPERTY_ID
    FROM b_catalog_iblock 
    WHERE IBLOCK_ID = %s
    """, (iblock_id,))
    
    catalog = cursor.fetchone()
    if catalog:
        print(f"  Каталог привязан: ✅")
        print(f"  Экспорт в Яндекс: {catalog['YANDEX_EXPORT']}")
        print(f"  ID товарного блока: {catalog['PRODUCT_IBLOCK_ID']}")
        print(f"  ID свойства SKU: {catalog['SKU_PROPERTY_ID']}")
    else:
        print("  ❌ Каталог не привязан к информационному блоку!")
        return
    
    # 3. Проверяем группы цен и их настройки
    print(f"\n💰 Группы цен:")
    cursor.execute("""
    SELECT ID, NAME, BASE, SORT 
    FROM b_catalog_group 
    ORDER BY SORT, ID
    """)
    
    groups = cursor.fetchall()
    for group in groups:
        base_mark = "🔥 БАЗОВАЯ" if group['BASE'] == 'Y' else ""
        print(f"  ID {group['ID']}: {group['NAME']} {base_mark}")
        print(f"    Сортировка: {group['SORT']}")
    
    # 4. Проверяем настройки отображения цен для тестового товара
    supplier_prefix = os.getenv('SUPPLIER_PREFIX', 'тов-')
    print(f"\n🧪 Тестовый товар Saturn:")
    
    cursor.execute("""
    SELECT 
        e.ID,
        e.NAME,
        e.ACTIVE,
        e.ACTIVE_FROM,
        e.ACTIVE_TO,
        prop.VALUE as ARTICLE,
        cat.QUANTITY,
        cat.QUANTITY_RESERVED,
        cat.PURCHASING_PRICE,
        cat.WEIGHT,
        cat.WIDTH,
        cat.LENGTH,
        cat.HEIGHT
    FROM b_iblock_element e
    LEFT JOIN b_iblock_element_property prop ON (
        e.ID = prop.IBLOCK_ELEMENT_ID 
        AND prop.IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
        )
    )
    LEFT JOIN b_catalog_product cat ON e.ID = cat.ID
    WHERE e.ACTIVE = 'Y' 
    AND e.IBLOCK_ID = %s
    AND prop.VALUE LIKE %s
    ORDER BY e.ID
    LIMIT 1
    """, (iblock_id, f"{supplier_prefix}%"))
    
    test_product = cursor.fetchone()
    if test_product:
        print(f"  📦 {test_product['ARTICLE']} (ID: {test_product['ID']})")
        print(f"    Название: {test_product['NAME']}")
        print(f"    Активен: {test_product['ACTIVE']}")
        print(f"    Количество: {test_product['QUANTITY']}")
        print(f"    Закупочная цена: {test_product['PURCHASING_PRICE']}")
        
        # Проверяем все цены этого товара
        cursor.execute("""
        SELECT 
            price.CATALOG_GROUP_ID,
            cg.NAME as GROUP_NAME,
            price.PRICE,
            price.CURRENCY,
            price.TIMESTAMP_X,
            price.QUANTITY_FROM,
            price.QUANTITY_TO
        FROM b_catalog_price price
        LEFT JOIN b_catalog_group cg ON price.CATALOG_GROUP_ID = cg.ID
        WHERE price.PRODUCT_ID = %s
        ORDER BY price.CATALOG_GROUP_ID
        """, (test_product['ID'],))
        
        prices = cursor.fetchall()
        print(f"    Цены:")
        for price in prices:
            print(f"      Группа {price['CATALOG_GROUP_ID']} ({price['GROUP_NAME']}): {price['PRICE']} {price['CURRENCY']}")
            print(f"        Обновлено: {price['TIMESTAMP_X']}")
            if price['QUANTITY_FROM'] or price['QUANTITY_TO']:
                print(f"        Количество: {price['QUANTITY_FROM']}-{price['QUANTITY_TO']}")
    
    # 5. Проверяем настройки модуля каталога
    print(f"\n⚙️ Настройки модуля каталога:")
    cursor.execute("""
    SELECT NAME, VALUE 
    FROM b_option 
    WHERE MODULE_ID = 'catalog' 
    AND NAME IN ('default_catalog_group', 'show_catalog_tab_with_offers', 'enable_reservation')
    ORDER BY NAME
    """)
    
    options = cursor.fetchall()
    for option in options:
        print(f"  {option['NAME']}: {option['VALUE']}")
    
    # 6. Проверяем права доступа к каталогу
    print(f"\n🔐 Права доступа к каталогу:")
    cursor.execute("""
    SELECT TASK_ID, OP_SREAD, OP_SEDIT 
    FROM b_iblock_right 
    WHERE IBLOCK_ID = %s 
    AND GROUP_CODE = 'G2'
    LIMIT 5
    """, (iblock_id,))
    
    rights = cursor.fetchall()
    if rights:
        for right in rights:
            print(f"  Задача {right['TASK_ID']}: чтение={right['OP_SREAD']}, редактирование={right['OP_SEDIT']}")
    else:
        print("  Права доступа не настроены или недоступны")
    
    # 7. Проверяем индексы каталога
    print(f"\n📊 Статистика индексации:")
    cursor.execute("""
    SELECT COUNT(*) as TOTAL_PRODUCTS
    FROM b_iblock_element 
    WHERE IBLOCK_ID = %s AND ACTIVE = 'Y'
    """, (iblock_id,))
    
    total = cursor.fetchone()
    print(f"  Всего активных товаров: {total['TOTAL_PRODUCTS']}")
    
    cursor.execute("""
    SELECT COUNT(*) as PRODUCTS_WITH_PRICES
    FROM b_iblock_element e
    INNER JOIN b_catalog_price p ON e.ID = p.PRODUCT_ID
    WHERE e.IBLOCK_ID = %s AND e.ACTIVE = 'Y'
    """, (iblock_id,))
    
    with_prices = cursor.fetchone()
    print(f"  Товаров с ценами: {with_prices['PRODUCTS_WITH_PRICES']}")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    try:
        debug_bitrix_catalog()
    except Error as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
