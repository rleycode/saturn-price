#!/usr/bin/env python3
"""
Full Sync - Полная синхронизация Saturn с Bitrix
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Optional

# Импорт наших модулей
from saturn_parser import SaturnParser, ProcessLock, load_skus_from_file
from bitrix_integration import BitrixClient, BitrixConfig, process_saturn_prices

logger = logging.getLogger(__name__)


class FullSyncManager:
    """Менеджер полной синхронизации"""
    
    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Файлы для этапов синхронизации
        self.raw_prices_file = self.output_dir / "saturn_raw_prices.csv"
        self.processed_prices_file = self.output_dir / "saturn_processed_prices.csv"
        
    def _load_config(self, config_file: str = None) -> BitrixConfig:
        """Загрузка конфигурации"""
        if config_file and Path(config_file).exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return BitrixConfig(**config_data)
        else:
            # Конфигурация из переменных окружения
            return BitrixConfig(
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
    
    def get_saturn_skus(self) -> List[str]:
        """Получение списка артикулов Saturn из Bitrix"""
        logger.info("Получение списка артикулов Saturn из Bitrix...")
        
        with BitrixClient(self.config) as bitrix:
            products = bitrix.get_products_by_prefix()
            
            # Извлекаем артикулы без префикса
            skus = []
            for product in products:
                saturn_sku = product.article.replace(self.config.supplier_prefix, '')
                skus.append(saturn_sku)
            
            logger.info(f"Найдено артикулов Saturn: {len(skus)}")
            return skus
    
    def stage1_parse_prices(self, skus: List[str] = None, batch_size: int = None) -> bool:
        """Этап 1: Парсинг цен с Saturn"""
        logger.info("=== ЭТАП 1: Парсинг цен с Saturn ===")
        
        if not skus:
            skus = self.get_saturn_skus()
        
        if not skus:
            logger.error("Нет артикулов для парсинга")
            return False
        
        # Ограничение размера пакета
        if batch_size and len(skus) > batch_size:
            logger.info(f"Ограничиваем до {batch_size} товаров")
            skus = skus[:batch_size]
        
        # Парсинг
        saturn_parser = SaturnParser()
        start_time = time.time()
        
        try:
            results = saturn_parser.parse_products(skus, str(self.raw_prices_file))
            elapsed = time.time() - start_time
            
            logger.info(f"Этап 1 завершен за {elapsed:.1f}с")
            logger.info(f"Спарсено товаров: {len(results)}/{len(skus)}")
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return False
    
    def stage2_process_markups(self) -> bool:
        """Этап 2: Применение наценок и обновление Bitrix"""
        logger.info("=== ЭТАП 2: Применение наценок и обновление Bitrix ===")
        
        if not self.raw_prices_file.exists():
            logger.error(f"Файл с ценами не найден: {self.raw_prices_file}")
            return False
        
        try:
            success = process_saturn_prices(
                str(self.raw_prices_file),
                self.config,
                str(self.processed_prices_file)
            )
            
            if success:
                logger.info("Этап 2 завершен успешно")
            else:
                logger.error("Этап 2 завершен с ошибками")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка обработки наценок: {e}")
            return False
    
    def run_full_sync(self, batch_size: int = None, skus_file: str = None) -> bool:
        """Запуск полной синхронизации"""
        logger.info("🚀 Запуск полной синхронизации Saturn → Bitrix")
        start_time = time.time()
        
        try:
            # Определение списка артикулов
            if skus_file:
                skus = load_skus_from_file(skus_file)
                logger.info(f"Загружено артикулов из файла: {len(skus)}")
            else:
                skus = None
            
            # Этап 1: Парсинг
            if not self.stage1_parse_prices(skus, batch_size):
                logger.error("Ошибка на этапе парсинга")
                return False
            
            # Этап 2: Наценки и обновление
            if not self.stage2_process_markups():
                logger.error("Ошибка на этапе обработки наценок")
                return False
            
            # Итоговая статистика
            elapsed = time.time() - start_time
            logger.info(f"✅ Полная синхронизация завершена за {elapsed:.1f}с")
            
            return True
            
        except Exception as e:
            logger.error(f"Критическая ошибка синхронизации: {e}")
            return False
    
    def cleanup_old_files(self, days: int = 7):
        """Очистка старых файлов"""
        logger.info(f"Очистка файлов старше {days} дней...")
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned_count = 0
        
        for file_path in self.output_dir.glob("*.csv"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                cleaned_count += 1
                logger.debug(f"Удален старый файл: {file_path}")
        
        logger.info(f"Удалено старых файлов: {cleaned_count}")


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Saturn Full Sync')
    parser.add_argument('--config', help='JSON файл с конфигурацией')
    parser.add_argument('--skus-file', help='Файл с артикулами для парсинга')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер пакета')
    parser.add_argument('--parse-only', action='store_true', help='Только парсинг без обновления Bitrix')
    parser.add_argument('--process-only', action='store_true', help='Только обработка существующего файла')
    parser.add_argument('--cleanup', action='store_true', help='Очистка старых файлов')
    parser.add_argument('--test-mode', action='store_true', help='Тестовый режим (ограниченное количество товаров)')
    
    args = parser.parse_args()
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Тестовый режим
    if args.test_mode:
        args.batch_size = min(args.batch_size, 10)
        logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: ограничено 10 товарами")
    
    # Блокировка одновременных запусков
    lock_file = "/tmp/saturn_full_sync.lock" if os.name != 'nt' else "saturn_full_sync.lock"
    
    try:
        with ProcessLock(lock_file):
            sync_manager = FullSyncManager(args.config)
            
            # Очистка старых файлов
            if args.cleanup:
                sync_manager.cleanup_old_files()
            
            # Выполнение синхронизации
            if args.parse_only:
                success = sync_manager.stage1_parse_prices(batch_size=args.batch_size)
            elif args.process_only:
                success = sync_manager.stage2_process_markups()
            else:
                success = sync_manager.run_full_sync(
                    batch_size=args.batch_size,
                    skus_file=args.skus_file
                )
            
            return 0 if success else 1
            
    except RuntimeError as e:
        logger.error(f"Ошибка блокировки: {e}")
        return 1
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
