#!/usr/bin/env python3
"""
Debug Bitrix Update - Проверка обновления цен в Bitrix для конкретного товара
"""

import os
import logging
from dotenv import load_dotenv
from bitrix_integration import BitrixClient, BitrixConfig

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def debug_product_114289():
    """Отладка товара 114289"""
    
    # Конфигурация
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    target_article = "тов-114289"
    test_price = 92.0
    
    logger.info(f"=== Отладка товара {target_article} ===")
    
    with BitrixClient(config) as bitrix:
        # 1. Найти товар в базе
        logger.info("1. Поиск товара в базе данных...")
        products = bitrix.get_products_by_prefix()
        
        target_product = None
        for product in products:
            if product.article == target_article:
                target_product = product
                break
        
        if not target_product:
            logger.error(f"Товар {target_article} не найден в базе!")
            return False
        
        logger.info(f"Найден товар: ID={target_product.id}, Name='{target_product.name}'")
        
        # 2. Проверить текущую цену
        logger.info("2. Проверка текущей цены...")
        cursor = bitrix.connection.cursor(dictionary=True)
        
        cursor.execute("""
        SELECT cp.ID, cp.PRICE, cp.CATALOG_GROUP_ID, cp.TIMESTAMP_X, cg.NAME as GROUP_NAME
        FROM b_catalog_price cp
        LEFT JOIN b_catalog_group cg ON cp.CATALOG_GROUP_ID = cg.ID
        WHERE cp.PRODUCT_ID = %s
        ORDER BY cp.CATALOG_GROUP_ID
        """, (target_product.id,))
        
        current_prices = cursor.fetchall()
        
        if current_prices:
            logger.info("Текущие цены:")
            for price in current_prices:
                logger.info(f"  Группа {price['CATALOG_GROUP_ID']} ({price['GROUP_NAME']}): {price['PRICE']} руб. (обновлено: {price['TIMESTAMP_X']})")
        else:
            logger.info("Цены для товара не найдены")
        
        # 3. Попытка обновления цены
        logger.info(f"3. Обновление цены на {test_price} руб...")
        
        success = bitrix.update_product_price(target_product.id, test_price, 1)
        
        if success:
            logger.info("✅ Цена успешно обновлена")
        else:
            logger.error("❌ Ошибка обновления цены")
            return False
        
        # 4. Проверка результата
        logger.info("4. Проверка результата обновления...")
        
        cursor.execute("""
        SELECT cp.ID, cp.PRICE, cp.CATALOG_GROUP_ID, cp.TIMESTAMP_X, cg.NAME as GROUP_NAME
        FROM b_catalog_price cp
        LEFT JOIN b_catalog_group cg ON cp.CATALOG_GROUP_ID = cg.ID
        WHERE cp.PRODUCT_ID = %s
        ORDER BY cp.CATALOG_GROUP_ID
        """, (target_product.id,))
        
        updated_prices = cursor.fetchall()
        
        if updated_prices:
            logger.info("Цены после обновления:")
            for price in updated_prices:
                logger.info(f"  Группа {price['CATALOG_GROUP_ID']} ({price['GROUP_NAME']}): {price['PRICE']} руб. (обновлено: {price['TIMESTAMP_X']})")
                
                if price['CATALOG_GROUP_ID'] == 1 and float(price['PRICE']) == test_price:
                    logger.info("✅ Цена успешно сохранена в базе данных!")
                    return True
        else:
            logger.error("❌ Цены не найдены после обновления")
            return False
        
        cursor.close()
        
        logger.error("❌ Цена не была корректно обновлена")
        return False

def check_catalog_structure():
    """Проверка структуры каталога"""
    
    config = BitrixConfig(
        mysql_host=os.getenv('BITRIX_MYSQL_HOST', '127.0.0.1'),
        mysql_port=int(os.getenv('BITRIX_MYSQL_PORT', 3306)),
        mysql_database=os.getenv('BITRIX_MYSQL_DATABASE', 'sitemanager'),
        mysql_username=os.getenv('BITRIX_MYSQL_USERNAME', 'bitrix_sync'),
        mysql_password=os.getenv('BITRIX_MYSQL_PASSWORD', ''),
        iblock_id=int(os.getenv('BITRIX_IBLOCK_ID', 11)),
        supplier_prefix=os.getenv('SUPPLIER_PREFIX', 'тов-')
    )
    
    logger.info("=== Проверка структуры каталога ===")
    
    with BitrixClient(config) as bitrix:
        cursor = bitrix.connection.cursor(dictionary=True)
        
        # Проверка групп цен
        logger.info("Группы цен:")
        cursor.execute("SELECT ID, NAME, BASE FROM b_catalog_group ORDER BY ID")
        price_groups = cursor.fetchall()
        
        for group in price_groups:
            base_flag = "BASE" if group['BASE'] == 'Y' else ""
            logger.info(f"  ID={group['ID']}: {group['NAME']} {base_flag}")
        
        # Проверка информационного блока
        logger.info(f"\nИнформационный блок {config.iblock_id}:")
        cursor.execute("SELECT ID, NAME, CODE FROM b_iblock WHERE ID = %s", (config.iblock_id,))
        iblock = cursor.fetchone()
        
        if iblock:
            logger.info(f"  Название: {iblock['NAME']}")
            logger.info(f"  Код: {iblock['CODE']}")
        else:
            logger.error(f"Информационный блок {config.iblock_id} не найден!")
        
        cursor.close()

if __name__ == '__main__':
    logger.info("🔍 Запуск отладки Bitrix интеграции")
    
    # Проверка структуры
    check_catalog_structure()
    
    print("\n" + "="*50 + "\n")
    
    # Отладка конкретного товара
    success = debug_product_114289()
    
    if success:
        logger.info("🎉 Отладка завершена успешно!")
    else:
        logger.error("💥 Обнаружены проблемы с обновлением цен")
