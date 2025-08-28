#!/usr/bin/env python3

import os
import sys
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('underprice_python')

@dataclass
class UnderpriceRule:
    id: int
    iblock_id: int
    section_id: Optional[int]
    price_code_from: str
    price_code_to: str
    percent: float
    sort: int

@dataclass
class ProductInfo:
    id: int
    name: str
    article: str
    section_id: Optional[int]
    current_price: Optional[float]

class UnderpriceProcessor:
    
    def __init__(self):
        self.connection = None
        self.rules = []
        self.processed_count = 0
        self.updated_count = 0
        self.price_groups = {}
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
                database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
                user=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
                password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
                charset='utf8mb4',
                autocommit=True,
                use_pure=True
            )
            logger.info(f"Подключение к MySQL установлено")
        except Error as e:
            logger.error(f"Ошибка подключения к MySQL: {e}")
            raise
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("Соединение с MySQL закрыто")
    
    def load_price_groups(self):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT ID, NAME, BASE FROM b_catalog_group ORDER BY SORT")
        
        for row in cursor.fetchall():
            self.price_groups[row['ID']] = {
                'name': row['NAME'],
                'base': row['BASE'] == 'Y'
            }
        
        cursor.close()
        logger.info(f"Загружено групп цен: {len(self.price_groups)}")
    
    def get_price_group_by_code(self, code: str) -> Optional[int]:
        code_mapping = {
            'BASE': 1,
            'RETAIL': 2,
            'WHOLESALE': 3,
            'VIP': 4
        }
        return code_mapping.get(code)
    
    def load_underprice_rules(self) -> List[UnderpriceRule]:
        cursor = self.connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT VALUE FROM b_option 
        WHERE MODULE_ID = 'mcart.underprice' AND NAME = 'SETTINGS_IBLOCK_ID'
        """)
        
        settings_row = cursor.fetchone()
        if not settings_row:
            logger.warning("Настройки модуля underprice не найдены")
            return []
        
        settings_iblock_id = int(settings_row['VALUE'])
        logger.info(f"ID блока настроек underprice: {settings_iblock_id}")
        
        query = """
        SELECT 
            e.ID,
            e.SORT,
            p_iblock.VALUE as IBLOCK_ID,
            p_section.VALUE as SECTION_ID,
            p_price_from.VALUE as PRICE_CODE_FROM_ENUM_ID,
            p_price_to.VALUE as PRICE_CODE_TO_ENUM_ID,
            p_percent.VALUE as PERCENT
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p_iblock ON (
            e.ID = p_iblock.IBLOCK_ELEMENT_ID 
            AND p_iblock.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'IBLOCK_ID'
            )
        )
        LEFT JOIN b_iblock_element_property p_section ON (
            e.ID = p_section.IBLOCK_ELEMENT_ID 
            AND p_section.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'SECTION_ID'
            )
        )
        LEFT JOIN b_iblock_element_property p_price_from ON (
            e.ID = p_price_from.IBLOCK_ELEMENT_ID 
            AND p_price_from.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PRICE_CODE'
            )
        )
        LEFT JOIN b_iblock_element_property p_price_to ON (
            e.ID = p_price_to.IBLOCK_ELEMENT_ID 
            AND p_price_to.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PRICE_CODE_TO'
            )
        )
        LEFT JOIN b_iblock_element_property p_percent ON (
            e.ID = p_percent.IBLOCK_ELEMENT_ID 
            AND p_percent.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PERCENT'
            )
        )
        WHERE e.IBLOCK_ID = %s AND e.ACTIVE = 'Y'
        ORDER BY e.SORT, e.ID
        """
        
        cursor.execute(query, (
            settings_iblock_id, settings_iblock_id, settings_iblock_id, 
            settings_iblock_id, settings_iblock_id, settings_iblock_id
        ))
        
        rules = []
        for row in cursor.fetchall():
            try:
                price_from_code = self.get_enum_xml_id(row['PRICE_CODE_FROM_ENUM_ID'])
                price_to_code = self.get_enum_xml_id(row['PRICE_CODE_TO_ENUM_ID'])
                
                if price_from_code and price_to_code:
                    rules.append(UnderpriceRule(
                        id=row['ID'],
                        iblock_id=int(row['IBLOCK_ID'] or 0),
                        section_id=int(row['SECTION_ID']) if row['SECTION_ID'] else None,
                        price_code_from=price_from_code,
                        price_code_to=price_to_code,
                        percent=float(row['PERCENT'] or 0),
                        sort=row['SORT'] or 500
                    ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка обработки правила {row['ID']}: {e}")
        
        cursor.close()
        logger.info(f"Загружено правил underprice: {len(rules)}")
        return rules
    
    def get_enum_xml_id(self, enum_id: int) -> Optional[str]:
        if not enum_id:
            return None
            
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("SELECT XML_ID FROM b_iblock_property_enum WHERE ID = %s", (enum_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        return row['XML_ID'] if row else None
    
    def get_products_for_processing(self, iblock_id: int, section_id: Optional[int] = None, 
                                   batch_size: int = 1000, offset: int = 0) -> List[ProductInfo]:
        cursor = self.connection.cursor(dictionary=True)
        
        where_conditions = ["e.ACTIVE = 'Y'", "e.IBLOCK_ID = %s"]
        params = [iblock_id]
        
        if section_id:
            where_conditions.append("e.IBLOCK_SECTION_ID = %s")
            params.append(section_id)
        
        query = f"""
        SELECT 
            e.ID,
            e.NAME,
            e.IBLOCK_SECTION_ID as SECTION_ID,
            prop.VALUE as ARTICLE
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property prop ON (
            e.ID = prop.IBLOCK_ELEMENT_ID 
            AND prop.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
            )
        )
        WHERE {' AND '.join(where_conditions)}
        ORDER BY e.ID
        LIMIT %s OFFSET %s
        """
        
        params.extend([batch_size, offset])
        cursor.execute(query, params)
        
        products = []
        for row in cursor.fetchall():
            products.append(ProductInfo(
                id=row['ID'],
                name=row['NAME'],
                article=row['ARTICLE'] or '',
                section_id=row['SECTION_ID'],
                current_price=None
            ))
        
        cursor.close()
        return products
    
    def get_product_price(self, product_id: int, price_group_id: int) -> Optional[float]:
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
        SELECT PRICE FROM b_catalog_price 
        WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = %s
        """, (product_id, price_group_id))
        
        row = cursor.fetchone()
        cursor.close()
        
        return float(row['PRICE']) if row else None
    
    def update_product_price(self, product_id: int, price_group_id: int, new_price: float) -> bool:
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
            SELECT ID FROM b_catalog_price 
            WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = %s
            """, (product_id, price_group_id))
            
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                UPDATE b_catalog_price 
                SET PRICE = %s, TIMESTAMP_X = NOW()
                WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = %s
                """, (new_price, product_id, price_group_id))
            else:
                cursor.execute("""
                INSERT INTO b_catalog_price 
                (PRODUCT_ID, CATALOG_GROUP_ID, PRICE, CURRENCY, TIMESTAMP_X)
                VALUES (%s, %s, %s, 'RUB', NOW())
                """, (product_id, price_group_id, new_price))
            
            return True
            
        except Error as e:
            logger.error(f"Ошибка обновления цены товара {product_id}: {e}")
            return False
        finally:
            cursor.close()
    
    def process_underprice_rules(self):
        logger.info("🔄 Начинаем обработку правил underprice...")
        start_time = datetime.now()
        
        self.load_price_groups()
        self.rules = self.load_underprice_rules()
        
        if not self.rules:
            logger.warning("Правила underprice не найдены")
            return
        
        for profile_id, rule in enumerate(self.rules):
            logger.info(f"📋 Profile {profile_id}: {rule.price_code_from} → {rule.price_code_to} ({rule.percent}%)")
            
            price_from_id = self.get_price_group_by_code(rule.price_code_from)
            price_to_id = self.get_price_group_by_code(rule.price_code_to)
            
            if not price_from_id or not price_to_id:
                logger.warning(f"Не найдены группы цен для правила {rule.id}")
                continue
            
            element_id = 0
            rule_processed = 0
            rule_updated = 0
            
            while True:
                products = self.get_products_batch(
                    rule.iblock_id, rule.section_id, element_id, 50
                )
                
                if not products:
                    break
                
                batch_processed = 0
                for product in products:
                    if rule.price_code_from == "P":
                        source_price = self.get_purchasing_price(product.id)
                    else:
                        source_price = self.get_product_price(product.id, price_from_id)
                    
                    if source_price is None or source_price <= 0:
                        continue
                    
                    new_price = source_price + (source_price * rule.percent / 100)
                    
                    if new_price > 0:
                        if rule.price_code_to == "P":
                            success = self.update_purchasing_price(product.id, new_price)
                        else:
                            success = self.update_product_price(product.id, price_to_id, new_price)
                        
                        if success:
                            rule_updated += 1
                            logger.debug(f"💰 {product.article}: {source_price} → {new_price:.2f} руб.")
                    
                    rule_processed += 1
                    batch_processed += 1
                    element_id = product.id
                
                self.processed_count += batch_processed
                
                if batch_processed < 50:
                    break
                
                logger.info(f"  📊 Обработано: {rule_processed}, обновлено: {rule_updated}")
            
            self.updated_count += rule_updated
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Обработка underprice завершена за {duration:.1f}с")
        logger.info(f"📈 Итого: обработано {self.processed_count}, обновлено {self.updated_count}")
    
    def get_products_batch(self, iblock_id: int, section_id: Optional[int], 
                          min_id: int, limit: int) -> List[ProductInfo]:
        cursor = self.connection.cursor(dictionary=True)
        
        where_conditions = [
            "e.ACTIVE = 'Y'", 
            "e.IBLOCK_ID = %s", 
            "e.ID > %s"
        ]
        params = [iblock_id, min_id]
        
        if section_id:
            where_conditions.append("e.IBLOCK_SECTION_ID = %s")
            params.append(section_id)
        
        where_conditions.append("cat.PURCHASING_PRICE IS NOT NULL")
        
        query = f"""
        SELECT 
            e.ID,
            e.NAME,
            e.IBLOCK_SECTION_ID as SECTION_ID,
            prop.VALUE as ARTICLE,
            cat.PURCHASING_PRICE
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property prop ON (
            e.ID = prop.IBLOCK_ELEMENT_ID 
            AND prop.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = e.IBLOCK_ID AND CODE = 'CML2_ARTICLE'
            )
        )
        LEFT JOIN b_catalog_product cat ON e.ID = cat.ID
        WHERE {' AND '.join(where_conditions)}
        ORDER BY e.ID ASC
        LIMIT %s
        """
        
        params.append(limit)
        cursor.execute(query, params)
        
        products = []
        for row in cursor.fetchall():
            products.append(ProductInfo(
                id=row['ID'],
                name=row['NAME'],
                article=row['ARTICLE'] or '',
                section_id=row['SECTION_ID'],
                current_price=float(row['PURCHASING_PRICE']) if row['PURCHASING_PRICE'] else None
            ))
        
        cursor.close()
        return products
    
    def get_purchasing_price(self, product_id: int) -> Optional[float]:
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute("""
        SELECT PURCHASING_PRICE FROM b_catalog_product 
        WHERE ID = %s
        """, (product_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        return float(row['PURCHASING_PRICE']) if row and row['PURCHASING_PRICE'] else None
    
    def update_purchasing_price(self, product_id: int, new_price: float) -> bool:
        cursor = self.connection.cursor()
        
        try:
            cursor.execute("""
            UPDATE b_catalog_product 
            SET PURCHASING_PRICE = %s, TIMESTAMP_X = NOW()
            WHERE ID = %s
            """, (new_price, product_id))
            
            return True
            
        except Error as e:
            logger.error(f"Ошибка обновления закупочной цены товара {product_id}: {e}")
            return False
        finally:
            cursor.close()

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    processor = UnderpriceProcessor()
    
    try:
        processor.connect()
        processor.process_underprice_rules()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    finally:
        processor.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
