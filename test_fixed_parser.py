#!/usr/bin/env python3
"""
Тест исправленного парсера Saturn
"""

from saturn_parser import SaturnParser

def test_fixed_parser():
    """Тест парсинга товара 103516"""
    
    parser = SaturnParser()
    
    print("🔍 Тестируем исправленный парсер")
    print("=" * 50)
    
    # Тестируем конкретный артикул
    sku = "103516"
    print(f"Парсим товар: {sku}")
    
    result = parser.parse_product(sku)
    
    if result:
        print("✅ Товар найден!")
        print(f"   Артикул: {result.sku}")
        print(f"   Название: {result.name}")
        print(f"   Цена: {result.price} руб.")
        print(f"   Наличие: {result.availability}")
        print(f"   URL: {result.url}")
    else:
        print("❌ Товар не найден")

if __name__ == "__main__":
    test_fixed_parser()
