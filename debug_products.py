#!/usr/bin/env python3
"""
Диагностика товаров в Bitrix для Saturn Parser
"""

import os
import sys
from bitrix_integration import BitrixClient, BitrixConfig
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_products():
    """Диагностика товаров в каталоге"""

    # Загружаем .env файл с явным указанием пути
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    
    # Отладочная информация
    print(f"🔧 Загружаем .env из: {env_path}")
    print(f"🔧 .env файл существует: {os.path.exists(env_path)}")
    
    # Проверяем загруженные переменные
    mysql_password = os.getenv('BITRIX_MYSQL_PASSWORD', '')
    print(f"🔧 MySQL пароль загружен: {'Да' if mysql_password else 'НЕТ'}")
    
    # Загрузка конфигурации из переменных окружения
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', 'localhost'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=mysql_password,
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    print(f"🔍 Диагностика товаров в каталоге {config.iblock_id}")
    print(f"📋 Ищем товары с префиксом: '{config.supplier_prefix}'")
    print("-" * 60)
    
    with BitrixClient(config) as bitrix:
        cursor = bitrix.connection.cursor(dictionary=True)
        
        # 1. Проверяем информационный блок
        print("1️⃣ Проверка информационного блока:")
        cursor.execute("""
        SELECT ID, NAME, CODE, ACTIVE 
        FROM b_iblock 
        WHERE ID = %s
        """, (config.iblock_id,))
        
        iblock = cursor.fetchone()
        if iblock:
            print(f"   ✅ ID: {iblock['ID']}, Название: {iblock['NAME']}, Активен: {iblock['ACTIVE']}")
        else:
            print(f"   ❌ Информационный блок {config.iblock_id} не найден!")
            return
        
        # 2. Проверяем поля для артикулов
        print("\n2️⃣ Доступные поля для артикулов:")
        cursor.execute("""
        SELECT ID, CODE, NAME, PROPERTY_TYPE 
        FROM b_iblock_property 
        WHERE IBLOCK_ID = %s 
        AND CODE IN ('CML2_ARTICLE', 'CML2_TRAIT_ARTIKUL', 'ARTICLE', 'SKU', 'ARTIKUL')
        ORDER BY CODE
        """, (config.iblock_id,))
        
        article_fields = cursor.fetchall()
        if article_fields:
            for field in article_fields:
                print(f"   📝 {field['CODE']}: {field['NAME']} (ID: {field['ID']})")
        else:
            print("   ❌ Поля для артикулов не найдены!")
        
        # 3. Общая статистика товаров
        print("\n3️⃣ Общая статистика товаров:")
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN ACTIVE = 'Y' THEN 1 END) as active
        FROM b_iblock_element 
        WHERE IBLOCK_ID = %s
        """, (config.iblock_id,))
        
        stats = cursor.fetchone()
        print(f"   📊 Всего товаров: {stats['total']}, активных: {stats['active']}")
        
        # 4. Проверяем товары с разными префиксами
        print("\n4️⃣ Поиск товаров по префиксам:")
        
        prefixes_to_check = ['тов-', 'saturn-', 'm-', 'товар-', 'тов_']
        
        for field in article_fields:
            print(f"\n   🔍 Поле {field['CODE']}:")
            
            for prefix in prefixes_to_check:
                cursor.execute("""
                SELECT COUNT(*) as count
                FROM b_iblock_element e
                LEFT JOIN b_iblock_element_property p ON (
                    e.ID = p.IBLOCK_ELEMENT_ID 
                    AND p.IBLOCK_PROPERTY_ID = %s
                )
                WHERE e.IBLOCK_ID = %s 
                AND e.ACTIVE = 'Y'
                AND p.VALUE LIKE %s
                """, (field['ID'], config.iblock_id, f"{prefix}%"))
                
                result = cursor.fetchone()
                count = result['count']
                if count > 0:
                    print(f"      ✅ '{prefix}*': {count} товаров")
                else:
                    print(f"      ⚪ '{prefix}*': 0 товаров")
        
        # 5. Примеры артикулов
        print("\n5️⃣ Примеры артикулов (первые 10):")
        
        if article_fields:
            main_field = article_fields[0]  # Берем первое поле
            cursor.execute("""
            SELECT p.VALUE as article, e.NAME
            FROM b_iblock_element e
            LEFT JOIN b_iblock_element_property p ON (
                e.ID = p.IBLOCK_ELEMENT_ID 
                AND p.IBLOCK_PROPERTY_ID = %s
            )
            WHERE e.IBLOCK_ID = %s 
            AND e.ACTIVE = 'Y'
            AND p.VALUE IS NOT NULL
            AND p.VALUE != ''
            ORDER BY e.ID
            LIMIT 10
            """, (main_field['ID'], config.iblock_id))
            
            examples = cursor.fetchall()
            if examples:
                for example in examples:
                    print(f"      📦 '{example['article']}' - {example['NAME'][:50]}...")
            else:
                print("      ❌ Примеры артикулов не найдены")
        
        # 6. Поиск товаров содержащих "saturn" или "сатурн"
        print("\n6️⃣ Поиск товаров содержащих 'saturn' или 'сатурн':")
        
        if article_fields:
            main_field = article_fields[0]
            
            search_terms = ['saturn', 'сатурн', 'Saturn', 'SATURN']
            
            for term in search_terms:
                cursor.execute("""
                SELECT COUNT(*) as count
                FROM b_iblock_element e
                LEFT JOIN b_iblock_element_property p ON (
                    e.ID = p.IBLOCK_ELEMENT_ID 
                    AND p.IBLOCK_PROPERTY_ID = %s
                )
                WHERE e.IBLOCK_ID = %s 
                AND e.ACTIVE = 'Y'
                AND (p.VALUE LIKE %s OR e.NAME LIKE %s)
                """, (main_field['ID'], config.iblock_id, f"%{term}%", f"%{term}%"))
                
                result = cursor.fetchone()
                count = result['count']
                if count > 0:
                    print(f"      ✅ Содержат '{term}': {count} товаров")
        
        cursor.close()
    
    print("\n" + "=" * 60)
    print("🎯 Рекомендации:")
    print("1. Проверьте правильность префикса SUPPLIER_PREFIX в .env")
    print("2. Убедитесь что товары Saturn есть в каталоге")
    print("3. Проверьте правильность поля для артикулов")


if __name__ == '__main__':
    debug_products()
