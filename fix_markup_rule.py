#!/usr/bin/env python3

import os
import logging
from dotenv import load_dotenv
from bitrix_integration import BitrixClient, BitrixConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def fix_saturn_markup_rule(new_markup_percent: float = -10.0):
    
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    logger.info(f"=== Исправление правила наценки Saturn на +{new_markup_percent}% ===")
    
    with BitrixClient(config) as bitrix:
        cursor = bitrix.connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT ID FROM b_iblock 
        WHERE ACTIVE = 'Y' 
        AND (NAME LIKE '%наценк%' OR CODE LIKE '%markup%' OR CODE LIKE '%price%')
        ORDER BY ID DESC
        LIMIT 1
        """)
        
        iblock_row = cursor.fetchone()
        if not iblock_row:
            logger.error("Информационный блок с наценками не найден")
            return False
        
        markup_iblock_id = iblock_row['ID']
        logger.info(f"Информационный блок наценок: {markup_iblock_id}")
        
        cursor.execute("""
        SELECT e.ID, e.NAME, p.VALUE as PERCENT
        FROM b_iblock_element e
        LEFT JOIN b_iblock_element_property p ON (
            e.ID = p.IBLOCK_ELEMENT_ID 
            AND p.IBLOCK_PROPERTY_ID = (
                SELECT ID FROM b_iblock_property 
                WHERE IBLOCK_ID = %s AND CODE = 'PERCENT'
            )
        )
        WHERE e.IBLOCK_ID = %s 
        AND e.NAME LIKE '%сатурн%'
        AND e.ACTIVE = 'Y'
        """, (markup_iblock_id, markup_iblock_id))
        
        saturn_rule = cursor.fetchone()
        if not saturn_rule:
            logger.error("Правило наценки Saturn не найдено")
            return False
        
        rule_id = saturn_rule['ID']
        current_percent = float(saturn_rule['PERCENT'] or 0)
        
        logger.info(f"Найдено правило: ID={rule_id}, '{saturn_rule['NAME']}'")
        logger.info(f"Текущая наценка: {current_percent}%")
        
        if current_percent == new_markup_percent:
            logger.info(f"Наценка уже установлена на {new_markup_percent}%")
            return True
        
        cursor.execute("""
        UPDATE b_iblock_element_property 
        SET VALUE = %s
        WHERE IBLOCK_ELEMENT_ID = %s 
        AND IBLOCK_PROPERTY_ID = (
            SELECT ID FROM b_iblock_property 
            WHERE IBLOCK_ID = %s AND CODE = 'PERCENT'
        )
        """, (new_markup_percent, rule_id, markup_iblock_id))
        
        new_name = f"Сатурн ({new_markup_percent:+.0f}%)"
        cursor.execute("""
        UPDATE b_iblock_element 
        SET NAME = %s
        WHERE ID = %s
        """, (new_name, rule_id))
        
        logger.info(f"✅ Правило обновлено: {current_percent}% → {new_markup_percent}%")
        logger.info(f"✅ Название изменено на: '{new_name}'")
        
        cursor.close()
        return True

def test_markup_after_fix():
    
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    logger.info("=== Тест наценки после исправления ===")
    
    from bitrix_integration import MarkupProcessor
    
    with BitrixClient(config) as bitrix:
        products = bitrix.get_products_by_prefix()
        target_product = None
        
        for product in products:
            if product.article == "тов-114289":
                target_product = product
                break
        
        if not target_product:
            logger.error("Товар тов-114289 не найден")
            return False
        
        markup_processor = MarkupProcessor(bitrix)
        markup_processor.load_markup_rules()
        
        original_price = 92.0
        final_price, markup_percent = markup_processor.apply_markup(target_product, original_price)
        
        logger.info(f"Тест наценки:")
        logger.info(f"  Исходная цена: {original_price} руб.")
        logger.info(f"  Наценка: {markup_percent}%")
        logger.info(f"  Итоговая цена: {final_price} руб.")
        
        if markup_percent == -10.0:
            logger.info("✅ Наценка установлена на -10%!")
            return True
        else:
            logger.error(f"❌ Наценка не соответствует ожидаемой: {markup_percent}%")
            return False

if __name__ == '__main__':
    logger.info("🔧 Запуск исправления правила наценки Saturn")
    
    if fix_saturn_markup_rule(-10.0):
        logger.info("✅ Правило наценки исправлено")
        
        if test_markup_after_fix():
            logger.info("🎉 Исправление завершено успешно!")
        else:
            logger.error("💥 Ошибка при тестировании")
    else:
        logger.error("💥 Ошибка исправления правила")
