#!/usr/bin/env python3
"""
Отладочный скрипт для проверки базы данных Bitrix
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_database():
    """Проверка базы данных и поиск товаров Saturn"""
    
    try:
        # Подключение к базе данных
        connection = mysql.connector.connect(
            host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
            port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
            database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
            user=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
            password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
            charset='utf8mb4'
        )
        
        cursor = connection.cursor(dictionary=True)
        print(f"✅ Подключение к базе данных установлено")
        
        # 1. Проверяем ID инфоблока
        iblock_id = int(os.getenv('BITRIX_IBLOCK_ID', 11))
        print(f"🔍 Проверяем инфоблок ID: {iblock_id}")
        
        cursor.execute("SELECT * FROM b_iblock WHERE ID = %s", (iblock_id,))
        iblock = cursor.fetchone()
        if iblock:
            print(f"✅ Инфоблок найден: {iblock['NAME']}")
        else:
            print(f"❌ Инфоблок с ID {iblock_id} не найден!")
            return
        
        # 2. Ищем свойство CML2_ARTICLE
        print(f"\n🔍 Ищем свойство CML2_ARTICLE в инфоблоке {iblock_id}")
        cursor.execute("""
            SELECT ID, NAME, CODE 
            FROM b_iblock_property 
            WHERE IBLOCK_ID = %s AND CODE = 'CML2_ARTICLE'
        """, (iblock_id,))
        
        article_property = cursor.fetchone()
        if article_property:
            property_id = article_property['ID']
            print(f"✅ Свойство CML2_ARTICLE найдено: ID = {property_id}")
        else:
            print(f"❌ Свойство CML2_ARTICLE не найдено в инфоблоке {iblock_id}!")
            
            # Показываем все свойства инфоблока
            cursor.execute("""
                SELECT ID, NAME, CODE 
                FROM b_iblock_property 
                WHERE IBLOCK_ID = %s 
                ORDER BY SORT, NAME
            """, (iblock_id,))
            
            properties = cursor.fetchall()
            print(f"\n📋 Все свойства инфоблока {iblock_id}:")
            for prop in properties[:10]:  # Показываем первые 10
                print(f"  ID: {prop['ID']}, CODE: {prop['CODE']}, NAME: {prop['NAME']}")
            return
        
        # 3. Ищем товары с префиксом "тов-"
        supplier_prefix = os.getenv('SUPPLIER_PREFIX', 'тов-')
        print(f"\n🔍 Ищем товары с префиксом '{supplier_prefix}'")
        
        query = """
        SELECT COUNT(*) as total_count
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p_article ON 
            e.ID = p_article.IBLOCK_ELEMENT_ID AND p_article.IBLOCK_PROPERTY_ID = %s
        WHERE e.IBLOCK_ID = %s 
            AND e.ACTIVE = 'Y'
            AND p_article.VALUE LIKE %s
        """
        
        cursor.execute(query, (property_id, iblock_id, f"{supplier_prefix}%"))
        result = cursor.fetchone()
        total_count = result['total_count']
        
        print(f"✅ Найдено товаров с префиксом '{supplier_prefix}': {total_count}")
        
        if total_count == 0:
            # Проверяем есть ли вообще товары в инфоблоке
            cursor.execute("SELECT COUNT(*) as total FROM b_iblock_element WHERE IBLOCK_ID = %s AND ACTIVE = 'Y'", (iblock_id,))
            total_products = cursor.fetchone()['total']
            print(f"📊 Всего активных товаров в инфоблоке: {total_products}")
            
            # Показываем примеры артикулов
            cursor.execute("""
                SELECT e.NAME, p_article.VALUE as ARTICLE
                FROM b_iblock_element e
                LEFT JOIN b_iblock_element_property p_article ON 
                    e.ID = p_article.IBLOCK_ELEMENT_ID AND p_article.IBLOCK_PROPERTY_ID = %s
                WHERE e.IBLOCK_ID = %s AND e.ACTIVE = 'Y' AND p_article.VALUE IS NOT NULL
                LIMIT 10
            """, (property_id, iblock_id))
            
            examples = cursor.fetchall()
            print(f"\n📋 Примеры артикулов в базе:")
            for example in examples:
                print(f"  {example['ARTICLE']} - {example['NAME']}")
        
        else:
            # Показываем примеры найденных товаров Saturn
            cursor.execute("""
                SELECT e.NAME, p_article.VALUE as ARTICLE
                FROM b_iblock_element e
                LEFT JOIN b_iblock_element_property p_article ON 
                    e.ID = p_article.IBLOCK_ELEMENT_ID AND p_article.IBLOCK_PROPERTY_ID = %s
                WHERE e.IBLOCK_ID = %s 
                    AND e.ACTIVE = 'Y'
                    AND p_article.VALUE LIKE %s
                LIMIT 5
            """, (property_id, iblock_id, f"{supplier_prefix}%"))
            
            saturn_products = cursor.fetchall()
            print(f"\n📋 Примеры товаров Saturn:")
            for product in saturn_products:
                print(f"  {product['ARTICLE']} - {product['NAME']}")
        
    except Error as e:
        print(f"❌ Ошибка базы данных: {e}")
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print(f"\n✅ Соединение с базой данных закрыто")

if __name__ == "__main__":
    check_database()
