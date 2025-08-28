#!/usr/bin/env python3
"""
Быстрый тест парсера Saturn
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from saturn_parser import SaturnParser

# Тест парсера
parser = SaturnParser()
result = parser.parse_product("103516")

if result:
    print(f"✅ Товар найден!")
    print(f"Артикул: {result.sku}")
    print(f"Название: {result.name}")
    print(f"Цена: {result.price} руб.")
    print(f"Наличие: {result.availability}")
else:
    print("❌ Товар не найден")
