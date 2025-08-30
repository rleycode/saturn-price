#!/usr/bin/env python3

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from saturn_parser import SaturnParser

def test_saturn_parser():
    """Тестируем старый saturn_parser.py на тех же SKU что и fast_saturn_parser"""
    
    # Те же тестовые SKU
    test_skus = ["014143", "137742", "089749"]
    
    print("🧪 ТЕСТИРОВАНИЕ SATURN_PARSER (СТАРЫЙ)")
    print("=" * 40)
    
    parser = SaturnParser()
    
    for sku in test_skus:
        print(f"\n🔍 Тестируем SKU: {sku}")
        print("-" * 30)
        
        try:
            result = parser.parse_product(sku)
            
            if result:
                print(f"✅ НАЙДЕН!")
                print(f"   SKU: {result.sku}")
                print(f"   Название: {result.name}")
                print(f"   Цена: {result.price}₽")
                print(f"   Наличие: {result.availability}")
                print(f"   URL: {result.url}")
            else:
                print(f"❌ НЕ НАЙДЕН")
                
        except Exception as e:
            print(f"💥 ОШИБКА: {e}")
    
    print(f"\n📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 30)
    
    # Тестируем все SKU разом
    try:
        results = parser.parse_products(test_skus)
        
        found_count = len(results)
        total_count = len(test_skus)
        
        print(f"Найдено: {found_count}/{total_count} товаров")
        
        if results:
            print("\nНайденные товары:")
            for result in results:
                print(f"  - {result.sku}: {result.price}₽ ({result.name[:50]}...)")
        
        not_found = [sku for sku in test_skus if not any(r.sku == sku for r in results)]
        if not_found:
            print(f"\nНе найдены: {', '.join(not_found)}")
        
    except Exception as e:
        print(f"💥 ОШИБКА МАССОВОГО ПАРСИНГА: {e}")

if __name__ == "__main__":
    test_saturn_parser()
