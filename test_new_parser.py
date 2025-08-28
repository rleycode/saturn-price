#!/usr/bin/env python3
"""
Тестирование исправленной логики парсинга Saturn
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from saturn_parser import SaturnParser, setup_logging

def test_new_parser():
    """Тестируем новую логику парсинга для товара тов-114289"""
    
    # Настройка логирования
    logger = setup_logging()
    
    print("🧪 Тестирование исправленной логики парсинга...")
    
    # Создаем парсер
    parser = SaturnParser()
    
    # Тестируем на проблемном артикуле
    test_sku = "114289"
    
    print(f"🔍 Парсинг товара: {test_sku}")
    
    try:
        result = parser.parse_product(test_sku)
        
        if result:
            print(f"✅ Товар найден!")
            print(f"  📝 Название: {result.name}")
            print(f"  💰 Цена: {result.price}₽")
            print(f"  🔗 URL: {result.url}")
            print(f"  🕐 Время: {result.parsed_at}")
            
            # Проверяем, что цена соответствует ожидаемой (92-99₽)
            if 90 <= result.price <= 100:
                print(f"✅ Цена в ожидаемом диапазоне (90-100₽)")
            else:
                print(f"⚠️ Цена {result.price}₽ не соответствует ожидаемой (92-99₽)")
        else:
            print(f"❌ Товар не найден")
            
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_parser()
