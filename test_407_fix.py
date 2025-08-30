#!/usr/bin/env python3

import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from fast_saturn_parser import FastSaturnParser

def test_407_fix():
    """Тестируем исправленный парсер на проблемных SKU с ценой 407₽"""
    
    # SKU которые ранее показывали неправильную цену 407.0₽
    problem_skus = ["216212", "205897", "190081", "192633", "190080", "145983"]
    
    # Добавляем известные рабочие SKU для сравнения
    working_skus = ["014143", "137742", "089749"]
    
    all_skus = problem_skus + working_skus
    
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОГО ПАРСЕРА")
    print("=" * 50)
    print(f"Проблемные SKU (ранее 407₽): {', '.join(problem_skus)}")
    print(f"Рабочие SKU: {', '.join(working_skus)}")
    print()
    
    parser = FastSaturnParser()
    
    found_count = 0
    problem_407_count = 0
    
    for sku in all_skus:
        print(f"🔍 Тестируем SKU: {sku}")
        
        try:
            result = parser.parse_single_product(sku)
            
            if result:
                found_count += 1
                print(f"✅ НАЙДЕН: {result.price}₽ - {result.name[:50]}...")
                
                # Проверяем на подозрительную цену 407₽
                if result.price == 407.0:
                    problem_407_count += 1
                    print(f"⚠️  ВНИМАНИЕ: Цена 407₽ - возможно неправильный товар!")
                    
            else:
                print(f"❌ НЕ НАЙДЕН")
                
        except Exception as e:
            print(f"💥 ОШИБКА: {e}")
        
        print()
    
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 30)
    print(f"Всего протестировано: {len(all_skus)} SKU")
    print(f"Найдено: {found_count}/{len(all_skus)} товаров")
    print(f"Товаров с ценой 407₽: {problem_407_count}")
    
    if problem_407_count == 0:
        print("🎉 ОТЛИЧНО! Проблема с ценой 407₽ решена!")
    else:
        print(f"⚠️  Все еще есть {problem_407_count} товаров с подозрительной ценой 407₽")

if __name__ == "__main__":
    test_407_fix()
