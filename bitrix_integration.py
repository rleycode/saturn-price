#!/usr/bin/env python3
"""
Bitrix Integration - Интеграция с системой Bitrix
"""

import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from pathlib import Path
import csv
import requests
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BitrixConfig:
    mysql_host: str
    mysql_port: int
    mysql_database: str
    mysql_username: str
    mysql_password: str
    iblock_id: int
    supplier_prefix: str = "saturn-"
    
    # Настройки модуля underprice
    underprice_url: Optional[str] = None
    underprice_password: Optional[str] = None


@dataclass
class BitrixMarkupRule:
    """Правило наценки из Bitrix"""
    id: int
    name: str
    section_id: Optional[int]
    price_code_from: str
    price_code_to: str
    markup_percent: float
    active: bool
    sort: int


@dataclass
class BitrixProduct:
    """Товар из каталога Bitrix"""
    id: int
    name: str
    article: str
    section_id: Optional[int]
    active: bool


class BitrixClient:
    """Клиент для работы с Bitrix"""
    
    def __init__(self, config: BitrixConfig):
        self.config = config
        self.connection = None
        self.logger = logging.getLogger(__name__)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def connect(self):
        """Подключение к MySQL Bitrix"""
        try:
            # Принудительно используем IPv4 для избежания проблем с ::1
            connection_config = {
                'host': self.config.mysql_host,
                'port': self.config.mysql_port,
                'database': self.config.mysql_database,
                'user': self.config.mysql_username,
                'password': self.config.mysql_password,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'autocommit': True,
                # Принудительно используем только IPv4
                'force_ipv6': False,
                'use_pure': True  # Использовать чистый Python коннектор
            }
            
            # Если host localhost, принудительно используем 127.0.0.1
            if self.config.mysql_host.lower() in ['localhost', '::1']:
                connection_config['host'] = '127.0.0.1'
                logger.debug("Принудительно используем IPv4 (127.0.0.1) вместо localhost")
            
            self.connection = mysql.connector.connect(**connection_config)
            logger.info(f"Подключение к Bitrix MySQL установлено: {connection_config['host']}:{self.config.mysql_port}")
            return True
        except Error as e:
            logger.error(f"Ошибка подключения к MySQL: {e}")
            return False
    
    def disconnect(self):
        """Отключение от MySQL"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Подключение к MySQL закрыто")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    def get_products_by_prefix(self) -> List[BitrixProduct]:
        """Получение товаров с префиксом Saturn"""
        if not self.connection:
            raise RuntimeError("Нет подключения к базе данных")
        
        cursor = self.connection.cursor(dictionary=True)
        
        # Сначала проверим, какие поля артикулов используются
        check_query = """
        SELECT DISTINCT p.CODE, COUNT(*) as count
        FROM b_iblock_property p
        WHERE p.IBLOCK_ID = %s 
        AND p.CODE IN ('CML2_ARTICLE', 'CML2_TRAIT_ARTIKUL', 'ARTICLE', 'SKU')
        GROUP BY p.CODE
        ORDER BY count DESC
        """
        
        cursor.execute(check_query, (self.config.iblock_id,))
        article_fields = cursor.fetchall()
        
        # Выбираем наиболее подходящее поле для артикулов
        article_field = 'CML2_ARTICLE'  # по умолчанию
        if article_fields:
            article_field = article_fields[0]['CODE']
            logger.info(f"Используем поле артикула: {article_field}")
        
        query = """
        SELECT 
            e.ID,
            e.NAME,
            e.ACTIVE,
            p_article.VALUE as ARTICLE
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p_article ON 
            e.ID = p_article.IBLOCK_ELEMENT_ID AND p_article.IBLOCK_PROPERTY_ID = 112
        WHERE e.IBLOCK_ID = %s 
            AND e.ACTIVE = 'Y'
            AND p_article.VALUE LIKE %s
        ORDER BY e.ID
        """
        
        cursor.execute(query, (
            self.config.iblock_id,
            f"{self.config.supplier_prefix}%"
        ))
        
        products = []
        for row in cursor.fetchall():
            products.append(BitrixProduct(
                id=row['ID'],
                name=row['NAME'],
                article=row['ARTICLE'],
                section_id=None,
                active=row['ACTIVE'] == 'Y'
            ))
        
        cursor.close()
        logger.info(f"Найдено товаров Saturn: {len(products)}")
        return products
    
    def get_markup_rule_for_product(self, product_id: int) -> Optional[Dict]:
        """Получение правила наценки для товара"""
        if not self.connection:
            raise RuntimeError("Нет подключения к базе данных")
        
        cursor = self.connection.cursor(dictionary=True)
        
        # Поиск информационного блока с наценками
        cursor.execute("""
        SELECT ID FROM b_iblock 
        WHERE ACTIVE = 'Y' 
        AND (NAME LIKE '%наценк%' OR CODE LIKE '%markup%' OR CODE LIKE '%price%')
        ORDER BY ID DESC
        LIMIT 1
        """)
        
        iblock_row = cursor.fetchone()
        if not iblock_row:
            logger.warning("Информационный блок с наценками не найден")
            return None
        
        markup_iblock_id = iblock_row['ID']
        logger.info(f"Используем информационный блок наценок: {markup_iblock_id}")
        
        article_query = """
        SELECT p_article.VALUE as ARTICLE
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p_article ON 
            e.ID = p_article.IBLOCK_ELEMENT_ID AND p_article.IBLOCK_PROPERTY_ID = 112
        WHERE e.ID = %s
        """
        
        cursor.execute(article_query, (product_id,))
        article_row = cursor.fetchone()
        if not article_row:
            logger.warning(f"Не найден артикул для товара {product_id}")
            return None
        
        article = article_row['ARTICLE']
        
        rule_patterns = {
            'pattern': article,
            'price_code': 'BASE',
            'extra': 0
        }
        
        query = """
        SELECT 
            e.ID,
            e.NAME,
            e.IBLOCK_SECTION_ID as SECTION_ID,
            e.ACTIVE,
            e.SORT,
            p1.VALUE as PRICE_CODE_FROM,
            p2.VALUE as PRICE_CODE_TO,
            p3.VALUE as MARKUP_PERCENT
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p1 ON (
            e.ID = p1.IBLOCK_ELEMENT_ID 
            AND p1.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PRICE_CODE'
            )
        )
        LEFT JOIN b_iblock_element_property p2 ON (
            e.ID = p2.IBLOCK_ELEMENT_ID 
            AND p2.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PRICE_CODE_TO'
            )
        )
        LEFT JOIN b_iblock_element_property p3 ON (
            e.ID = p3.IBLOCK_ELEMENT_ID 
            AND p3.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PERCENT'
            )
        )
        WHERE e.IBLOCK_ID = %s 
        AND e.ACTIVE = 'Y'
        ORDER BY e.SORT, e.ID
        """
        
        cursor.execute(query, (
            markup_iblock_id, markup_iblock_id, markup_iblock_id, markup_iblock_id
        ))
        
        rules = []
        for row in cursor.fetchall():
            try:
                markup_percent = float(row['MARKUP_PERCENT'] or 0)
                rules.append({
                    'id': row['ID'],
                    'name': row['NAME'],
                    'section_id': row['SECTION_ID'],
                    'price_code_from': row['PRICE_CODE_FROM'] or 'BASE',
                    'price_code_to': row['PRICE_CODE_TO'] or 'BASE',
                    'markup_percent': markup_percent,
                    'active': row['ACTIVE'] == 'Y',
                    'sort': row['SORT'] or 500
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Ошибка обработки правила {row['ID']}: {e}")
        
        cursor.close()
        
        for rule in rules:
            if self.is_markup_rule_applicable(rule, article):
                return rule
        
        return None
    
    def is_markup_rule_applicable(self, rule: Dict, article: str) -> bool:
        """Проверка применимости правила наценки"""
        if rule['section_id'] is None:
            return True
        
        # TODO: реализовать логику проверки применимости правила
        
        return False
    
    def update_product_price(self, product_id: int, new_price: float, old_price: float = None) -> bool:
        """Обновление цены товара в Bitrix"""
        if not self.connection:
            raise RuntimeError("Нет подключения к базе данных")
        
        cursor = self.connection.cursor()
        
        try:
            query = """
                SELECT cp.PRICE 
                FROM b_catalog_price cp
                WHERE cp.PRODUCT_ID = %s 
                    AND cp.CATALOG_GROUP_ID = 1
                ORDER BY cp.ID DESC
                LIMIT 1
            """
            
            cursor.execute(query, (product_id,))
            existing_price = cursor.fetchone()
            
            if existing_price:
                update_query = """
                    UPDATE b_catalog_price 
                    SET PRICE = %s, PRICE_SCALE = %s
                    WHERE PRODUCT_ID = %s AND CATALOG_GROUP_ID = 1
                """
                cursor.execute(update_query, (new_price, new_price, product_id))
                logger.debug(f"Обновлена цена для товара {product_id}: {old_price} → {new_price} руб.")
            else:
                if cursor.rowcount == 0:
                    insert_query = """
                        INSERT INTO b_catalog_price 
                        (PRODUCT_ID, CATALOG_GROUP_ID, PRICE, CURRENCY, TIMESTAMP_X)
                        VALUES (%s, %s, %s, 'RUB', NOW())
                    """
                    cursor.execute(insert_query, (product_id, 1, new_price))
                    logger.debug(f"Создана новая цена для товара {product_id}: {new_price} руб.")
            
            # autocommit=True уже установлен, commit() не нужен
            return True
            
        except Error as e:
            logger.error(f"Ошибка обновления цены для товара {product_id}: {e}")
            logger.error(f"SQL ошибка: {e}")
            return False
        finally:
            cursor.close()
    
    def trigger_underprice_module(self, product_id: int):
        """Запуск модуля underprice для пересчета скидок"""
        try:
            # Используем новый Python модуль underprice вместо HTTP запроса
            from underprice_python import UnderpriceProcessor
            
            logger.info("Запускаем Python модуль underprice...")
            processor = UnderpriceProcessor()
            processor.connect()
            processor.process_underprice_rules()
            processor.disconnect()
            
            logger.info("Модуль underprice успешно выполнен")
            return True
            
        except ImportError:
            # Fallback на старый HTTP метод если новый модуль недоступен
            logger.warning("Python модуль underprice недоступен, используем HTTP метод")
            return self._trigger_underprice_http()
        except Exception as e:
            logger.error(f"Ошибка выполнения underprice: {e}")
            return False
    
    def _trigger_underprice_http(self):
        """Запуск underprice через HTTP (fallback метод)"""
        if not self.config.underprice_url or not self.config.underprice_password:
            logger.info("Настройки underprice не заданы, пропускаем")
            return True
        
        try:
            response = requests.post(self.config.underprice_url, data={'password': self.config.underprice_password}, timeout=30)
            
            if response.status_code == 200:
                logger.info("Модуль underprice успешно запущен")
                return True
            else:
                logger.error(f"Ошибка запуска underprice: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка запроса к underprice: {e}")
            return False


class MarkupProcessor:
    """Обработчик наценок"""
    
    def __init__(self, bitrix_client: BitrixClient):
        self.bitrix_client = bitrix_client
        self.markup_rules = []
    
    def load_markup_rules(self):
        """Загрузка правил наценок"""
        self.markup_rules = self.bitrix_client.get_markup_rules()
    
    def apply_markup(self, product: BitrixProduct, original_price: float) -> Tuple[float, float]:
        """Применение наценки к цене товара"""
        # Ищем правило наценки в инфоблоке Bitrix
        markup_rule = self.bitrix_client.get_markup_rule_for_product(product.id)
        
        if markup_rule:
            markup_percent = markup_rule['markup_percent']
            final_price = original_price * (1 + markup_percent / 100)
            logger.debug(f"Товар {product.article}: {original_price} → {final_price:.2f} ({markup_percent:+.1f}%)")
            return final_price, markup_percent
        else:
            # Для товаров Saturn применяем скидку -10% по умолчанию
            if product.article.startswith('тов-'):
                saturn_markup = -10.0  # Скидка 10% для Saturn
                final_price = original_price * (1 + saturn_markup / 100)
                logger.debug(f"Товар Saturn {product.article}: {original_price} → {final_price:.2f} ({saturn_markup}% по умолчанию)")
                return final_price, saturn_markup
            else:
                # Базовая наценка по умолчанию для других товаров
                default_markup = 30.0
                final_price = original_price * (1 + default_markup / 100)
                logger.debug(f"Товар {product.article}: {original_price} → {final_price:.2f} (+{default_markup}% по умолчанию)")
                return final_price, default_markup


def process_saturn_prices(input_csv: str, config: BitrixConfig, output_csv: str = None) -> bool:
    """Обработка цен Saturn с применением наценок и обновлением Bitrix"""
    
    logger.info(f"Обработка файла: {input_csv}")
    
    # Загрузка данных из CSV
    saturn_prices = {}
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            sku = row['sku']
            try:
                price = float(row['price'])
                saturn_prices[sku] = {
                    'name': row['name'],
                    'price': price,
                    'availability': row['availability'],
                    'url': row['url']
                }
            except (ValueError, KeyError) as e:
                logger.warning(f"Ошибка обработки строки для {sku}: {e}")
    
    logger.info(f"Загружено цен Saturn: {len(saturn_prices)}")
    
    bitrix_client = BitrixClient(config)
    
    # Загрузка товаров
    products = bitrix_client.get_products_by_prefix()
    
    # Обработка товаров
    processed_count = 0
    updated_count = 0
    results = []
    
    for product in products:
        # Удаляем префикс для поиска в Saturn
        saturn_sku = product.article.replace(config.supplier_prefix, '')
        
        if saturn_sku in saturn_prices:
            saturn_data = saturn_prices[saturn_sku]
            original_price = saturn_data['price']
            
            # Применение наценки
            final_price, markup_percent = MarkupProcessor(bitrix_client).apply_markup(product, original_price)
            
            # Обновление цены в Bitrix
            if bitrix_client.update_product_price(product.id, final_price, original_price):
                updated_count += 1
                logger.info(f"✅ {product.article}: {original_price} → {final_price:.2f} руб.")
            else:
                logger.error(f"❌ Ошибка обновления цены для {product.article}")
            
            # Сохранение результата
            results.append({
                'sku': product.article,
                'name': product.name,
                'original_price': original_price,
                'markup_percent': markup_percent,
                'final_price': final_price,
                'section_id': product.section_id,
                'updated_at': datetime.now().isoformat()
            })
            
            processed_count += 1
    
    # Сохранение результатов в CSV
    if output_csv and results:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys(), delimiter=';')
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"Результаты сохранены: {output_csv}")
    
    # Запуск модуля скидок
    if updated_count > 0:
        logger.info("Запускаем пересчет скидок...")
        for product in products:
            bitrix_client.trigger_underprice_module(product.id)
    
    logger.info(f"Обработка завершена. Обработано: {processed_count}, обновлено: {updated_count}")
    return updated_count > 0


def main():
    """Главная функция для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bitrix Integration')
    parser.add_argument('input_csv', help='CSV файл с ценами Saturn')
    parser.add_argument('--output', help='Выходной CSV файл')
    parser.add_argument('--config', help='JSON файл с конфигурацией')
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        config = BitrixConfig(**config_data)
    else:
        # Конфигурация по умолчанию из переменных окружения
        import os
        config = BitrixConfig(
            mysql_host=os.getenv('BITRIX_MYSQL_HOST', 'localhost'),
            mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
            mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
            mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
            mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
            iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
            supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'saturn-'),
            underprice_url=os.getenv('SATURN_UNDERPRICE_URL'),
            underprice_password=os.getenv('SATURN_UNDERPRICE_PASSWORD')
        )
    
    # Обработка
    success = process_saturn_prices(args.input_csv, config, args.output)
    return 0 if success else 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
