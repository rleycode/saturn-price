#!/usr/bin/env python3
"""
Тестирование fast_saturn_parser на конкретных SKU
"""

import sys
from fast_saturn_parser import FastSaturnParser

def test_specific_skus():
    """Тестируем конкретные проблемные SKU"""
    
    test_skus = ['014143', '137742', '089749']
    
    print("🧪 ТЕСТИРОВАНИЕ FAST_SATURN_PARSER")
    print("=" * 40)
    
    parser = FastSaturnParser()
    
    for sku in test_skus:
        print(f"\n🔍 Тестируем SKU: {sku}")
        print("-" * 30)
        
        try:
            result = parser.parse_single_product(sku)
            
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
        results = parser.parse_products_batch(test_skus)
        
        found_count = len(results)
        total_count = len(test_skus)
        
        print(f"Найдено: {found_count}/{total_count} товаров")
        
        if results:
            print("\nНайденные товары:")
            for result in results:
                print(f"  - {result.sku}: {result.price}₽ ({result.name[:50]}...)")
        
        missing_skus = set(test_skus) - {r.sku for r in results}
        if missing_skus:
            print(f"\nНе найдены: {', '.join(missing_skus)}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"💥 ОШИБКА МАССОВОГО ПАРСИНГА: {e}")
        return False

def main():
    success = test_specific_skus()
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
