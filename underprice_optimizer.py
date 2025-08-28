#!/usr/bin/env python3
"""
Оптимизированный модуль пересчета скидок (замена underprice.php)
Прямая работа с базой данных для максимальной производительности
"""

import os
import sys
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# Настройка логирования
logger = logging.getLogger('underprice_optimizer')

@dataclass
class PriceRule:
    """Правило расчета скидки"""
    section_id: int
    min_price: float
    max_price: float
    discount_percent: float
    priority: int

@dataclass
class ProductPrice:
    """Цена товара"""
    product_id: int
    price: float
    section_id: int
    article: str

class UnderpriceOptimizer:
    """Оптимизированный пересчет скидок"""
    
    def __init__(self, mysql_config: dict):
        self.mysql_config = mysql_config
        self.connection = None
        self.processed_count = 0
        self.updated_count = 0
    
    def connect(self):
        """Подключение к MySQL"""
        try:
            self.connection = mysql.connector.connect(
                host=self.mysql_config['host'],
                port=self.mysql_config['port'],
                database=self.mysql_config['database'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                charset='utf8mb4',
                autocommit=True,
                use_pure=True
            )
            logger.info(f"Подключение к MySQL: {self.mysql_config['host']}:{self.mysql_config['port']}")
        except Error as e:
            logger.error(f"Ошибка подключения к MySQL: {e}")
            raise
    
    def disconnect(self):
        """Отключение от MySQL"""
        if self.connection:
            self.connection.close()
            logger.info("Соединение с MySQL закрыто")
    
    def get_discount_rules(self, iblock_id: int) -> List[PriceRule]:
        """Получение правил скидок из информационного блока"""
        cursor = self.connection.cursor(dictionary=True)
        
        # Получаем правила скидок (предполагаем структуру)
        query = """
        SELECT 
            e.ID,
            e.IBLOCK_SECTION_ID as SECTION_ID,
            p1.VALUE as MIN_PRICE,
            p2.VALUE as MAX_PRICE,
            p3.VALUE as DISCOUNT_PERCENT,
            e.SORT as PRIORITY
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p1 ON (
            e.ID = p1.IBLOCK_ELEMENT_ID 
            AND p1.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'MIN_PRICE'
            )
        )
        LEFT JOIN b_iblock_element_property p2 ON (
            e.ID = p2.IBLOCK_ELEMENT_ID 
            AND p2.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'MAX_PRICE'
            )
        )
        LEFT JOIN b_iblock_element_property p3 ON (
            e.ID = p3.IBLOCK_ELEMENT_ID 
            AND p3.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'DISCOUNT_PERCENT'
            )
        )
        WHERE e.IBLOCK_ID = %s AND e.ACTIVE = 'Y'
        ORDER BY e.SORT, e.ID
        """
        
        cursor.execute(query, (iblock_id, iblock_id, iblock_id, iblock_id))
        
        rules = []
        for row in cursor.fetchall():
            try:
                rules.append(PriceRule(
                    section_id=row['SECTION_ID'] or 0,
                    min_price=float(row['MIN_PRICE'] or 0),
                    max_price=float(row['MAX_PRICE'] or 999999),
                    discount_percent=float(row['DISCOUNT_PERCENT'] or 0),
                    priority=row['PRIORITY'] or 500
                ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка обработки правила скидки {row['ID']}: {e}")
        
        cursor.close()
        logger.info(f"Загружено правил скидок: {len(rules)}")
        return rules
    
    def get_products_with_prices(self, supplier_prefix: str, batch_size: int = 1000) -> List[ProductPrice]:
        """Получение товаров с ценами пакетами"""
        cursor = self.connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            e.ID as PRODUCT_ID,
            e.NAME,
            e.IBLOCK_SECTION_ID as SECTION_ID,
            prop.VALUE as ARTICLE,
            price.PRICE
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property prop ON (
            e.ID = prop.IBLOCK_ELEMENT_ID 
            AND prop.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
            )
        )
        LEFT JOIN b_catalog_price price ON (
            e.ID = price.PRODUCT_ID 
            AND price.CATALOG_GROUP_ID = 1
        )
        WHERE e.ACTIVE = 'Y' 
        AND prop.VALUE LIKE %s
        AND price.PRICE IS NOT NULL
        ORDER BY e.ID
        LIMIT %s
        """
        
        cursor.execute(query, (f"{supplier_prefix}%", batch_size))
        
        products = []
        for row in cursor.fetchall():
            products.append(ProductPrice(
                product_id=row['PRODUCT_ID'],
                price=float(row['PRICE']),
                section_id=row['SECTION_ID'] or 0,
                article=row['ARTICLE'] or ''
            ))
        
        cursor.close()
        return products
    
    def find_applicable_discount(self, product: ProductPrice, rules: List[PriceRule]) -> Optional[PriceRule]:
        """Поиск применимого правила скидки"""
        applicable_rules = []
        
        for rule in rules:
            # Проверяем секцию (0 = для всех секций)
            if rule.section_id != 0 and rule.section_id != product.section_id:
                continue
            
            # Проверяем диапазон цен
            if product.price < rule.min_price or product.price > rule.max_price:
                continue
            
            applicable_rules.append(rule)
        
        # Возвращаем правило с наивысшим приоритетом (меньшее число = выше приоритет)
        if applicable_rules:
            return min(applicable_rules, key=lambda r: r.priority)
        
        return None
    
    def update_product_discount(self, product_id: int, discount_price: float) -> bool:
        """Обновление цены со скидкой"""
        cursor = self.connection.cursor()
        
        try:
            # Обновляем цену в группе скидок (например, группа 2)
            cursor.execute("""
            INSERT INTO b_catalog_price 
            (PRODUCT_ID, CATALOG_GROUP_ID, PRICE, CURRENCY, TIMESTAMP_X)
            VALUES (%s, 2, %s, 'RUB', NOW())
            ON DUPLICATE KEY UPDATE 
            PRICE = VALUES(PRICE), 
            TIMESTAMP_X = NOW()
            """, (product_id, discount_price))
            
            return True
            
        except Error as e:
            logger.error(f"Ошибка обновления скидки для товара {product_id}: {e}")
            return False
        finally:
            cursor.close()
    
    def process_discounts(self, supplier_prefix: str, discount_iblock_id: int, batch_size: int = 1000):
        """Основной процесс пересчета скидок"""
        logger.info("🔄 Начинаем пересчет скидок...")
        start_time = datetime.now()
        
        # Загружаем правила скидок
        rules = self.get_discount_rules(discount_iblock_id)
        if not rules:
            logger.warning("Правила скидок не найдены")
            return
        
        # Обрабатываем товары пакетами
        offset = 0
        total_processed = 0
        
        while True:
            # Получаем пакет товаров
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("""
            SELECT 
                e.ID as PRODUCT_ID,
                e.IBLOCK_SECTION_ID as SECTION_ID,
                prop.VALUE as ARTICLE,
                price.PRICE
            FROM b_iblock_element e
            LEFT JOIN b_iblock_element_property prop ON (
                e.ID = prop.IBLOCK_ELEMENT_ID 
                AND prop.IBLOCK_PROPERTY_ID = (
                    SELECT ID FROM b_iblock_property 
                    WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
                )
            )
            LEFT JOIN b_catalog_price price ON (
                e.ID = price.PRODUCT_ID 
                AND price.CATALOG_GROUP_ID = 1
            )
            WHERE e.ACTIVE = 'Y' 
            AND prop.VALUE LIKE %s
            AND price.PRICE IS NOT NULL
            ORDER BY e.ID
            LIMIT %s OFFSET %s
            """, (f"{supplier_prefix}%", batch_size, offset))
            
            products = cursor.fetchall()
            cursor.close()
            
            if not products:
                break
            
            # Обрабатываем каждый товар
            for row in products:
                product = ProductPrice(
                    product_id=row['PRODUCT_ID'],
                    price=float(row['PRICE']),
                    section_id=row['SECTION_ID'] or 0,
                    article=row['ARTICLE'] or ''
                )
                
                # Находим применимое правило скидки
                discount_rule = self.find_applicable_discount(product, rules)
                
                if discount_rule:
                    # Рассчитываем цену со скидкой
                    discount_price = product.price * (1 - discount_rule.discount_percent / 100)
                    
                    # Обновляем цену со скидкой
                    if self.update_product_discount(product.product_id, discount_price):
                        self.updated_count += 1
                        logger.debug(f"💰 {product.article}: {product.price} → {discount_price:.2f} руб. (-{discount_rule.discount_percent}%)")
                
                self.processed_count += 1
            
            total_processed += len(products)
            logger.info(f"📊 Обработано товаров: {total_processed}, обновлено скидок: {self.updated_count}")
            
            offset += batch_size
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Пересчет скидок завершен за {duration:.1f}с")
        logger.info(f"📈 Итого: обработано {self.processed_count}, обновлено {self.updated_count}")

def main():
    """Главная функция"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Конфигурация из переменных окружения
    mysql_config = {
        'host': os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        'port': int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        'database': os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        'user': os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        'password': os.getenv('BITRIX_MYSQL_PASSWORD', '')
    }
    
    supplier_prefix = os.getenv('SUPPLIER_PREFIX', 'тов-')
    discount_iblock_id = int(os.getenv('DISCOUNT_IBLOCK_ID', 39))  # ID блока правил скидок
    batch_size = int(os.getenv('SATURN_BATCH_SIZE', 1000))
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    optimizer = UnderpriceOptimizer(mysql_config)
    
    try:
        optimizer.connect()
        optimizer.process_discounts(supplier_prefix, discount_iblock_id, batch_size)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    finally:
        optimizer.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
