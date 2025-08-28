#!/usr/bin/env python3
"""
Проверка кеширования и настроек отображения цен в Bitrix
"""

import os
import sys
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def check_bitrix_cache():
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
    
    print("🔍 Проверка настроек кеширования и отображения...")
    
    # 1. Проверяем настройки кеширования
    print("\n💾 Настройки кеша:")
    cursor.execute("""
    SELECT NAME, VALUE 
    FROM b_option 
    WHERE MODULE_ID = 'main' 
    AND NAME IN ('cache_flags', 'cache_time', 'use_cache')
    ORDER BY NAME
    """)
    
    cache_options = cursor.fetchall()
    for option in cache_options:
        print(f"  {option['NAME']}: {option['VALUE']}")
    
    # 2. Проверяем настройки каталога
    print("\n🛒 Настройки модуля каталога:")
    cursor.execute("""
    SELECT NAME, VALUE 
    FROM b_option 
    WHERE MODULE_ID = 'catalog' 
    AND NAME IN ('default_can_buy_zero', 'show_catalog_tab_with_offers', 'price_precision')
    ORDER BY NAME
    """)
    
    catalog_options = cursor.fetchall()
    for option in catalog_options:
        print(f"  {option['NAME']}: {option['VALUE']}")
    
    # 3. Проверяем настройки информационных блоков
    print("\n📋 Настройки информационного блока:")
    iblock_id = int(os.getenv('BITRIX_IBLOCK_ID', 11))
    cursor.execute("""
    SELECT NAME, VALUE 
    FROM b_option 
    WHERE MODULE_ID = 'iblock' 
    AND NAME IN ('cache_time', 'use_htmledit')
    ORDER BY NAME
    """)
    
    iblock_options = cursor.fetchall()
    for option in iblock_options:
        print(f"  {option['NAME']}: {option['VALUE']}")
    
    # 4. Проверяем настройки сайта
    print("\n🌐 Настройки сайта:")
    cursor.execute("""
    SELECT LID, ACTIVE, NAME, DIR, DOMAIN_LIMITED 
    FROM b_lang 
    WHERE ACTIVE = 'Y'
    """)
    
    sites = cursor.fetchall()
    for site in sites:
        print(f"  Сайт {site['LID']}: {site['NAME']}")
        print(f"    Активен: {site['ACTIVE']}")
        print(f"    Директория: {site['DIR']}")
        print(f"    Домен ограничен: {site['DOMAIN_LIMITED']}")
    
    # 5. Проверяем агентов (возможно влияют на обновление цен)
    print("\n🤖 Активные агенты каталога:")
    cursor.execute("""
    SELECT NAME, ACTIVE, LAST_EXEC, NEXT_EXEC 
    FROM b_agent 
    WHERE MODULE_ID = 'catalog' 
    AND ACTIVE = 'Y'
    ORDER BY NEXT_EXEC
    LIMIT 5
    """)
    
    agents = cursor.fetchall()
    for agent in agents:
        print(f"  {agent['NAME']}")
        print(f"    Последний запуск: {agent['LAST_EXEC']}")
        print(f"    Следующий запуск: {agent['NEXT_EXEC']}")
    
    # 6. Проверяем индексы поиска
    print("\n🔍 Состояние поисковых индексов:")
    cursor.execute("""
    SELECT MODULE_ID, ITEM_ID, DATE_CHANGE 
    FROM b_search_content 
    WHERE MODULE_ID = 'iblock' 
    ORDER BY DATE_CHANGE DESC 
    LIMIT 5
    """)
    
    search_index = cursor.fetchall()
    for index in search_index:
        print(f"  Модуль: {index['MODULE_ID']}, ID: {index['ITEM_ID']}")
        print(f"    Обновлен: {index['DATE_CHANGE']}")
    
    # 7. Проверяем состояние конкретного товара в поиске
    print("\n🧪 Тестовый товар в поисковом индексе:")
    cursor.execute("""
    SELECT sc.ITEM_ID, sc.TITLE, sc.BODY, sc.DATE_CHANGE
    FROM b_search_content sc
    WHERE sc.MODULE_ID = 'iblock' 
    AND sc.ITEM_ID = 776
    """)
    
    search_product = cursor.fetchone()
    if search_product:
        print(f"  Товар ID 776 найден в индексе")
        print(f"  Заголовок: {search_product['TITLE']}")
        print(f"  Обновлен: {search_product['DATE_CHANGE']}")
        # Проверяем, есть ли цена в индексе
        if '82.80' in str(search_product['BODY']) or '82,80' in str(search_product['BODY']):
            print("  ✅ Цена найдена в поисковом индексе")
        else:
            print("  ❌ Цена НЕ найдена в поисковом индексе")
    else:
        print("  ❌ Товар ID 776 НЕ найден в поисковом индексе")
    
    # 8. Проверяем права доступа к ценам
    print("\n🔐 Права доступа к каталогу:")
    cursor.execute("""
    SELECT gr.STRING_ID, gr.NAME
    FROM b_group gr
    WHERE gr.ACTIVE = 'Y' 
    AND gr.ID IN (1, 2)
    ORDER BY gr.ID
    """)
    
    groups = cursor.fetchall()
    for group in groups:
        print(f"  Группа: {group['STRING_ID']} ({group['NAME']})")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    try:
        check_bitrix_cache()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
