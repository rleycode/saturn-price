#!/usr/bin/env python3
"""
Прямой тест парсера с отладкой
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ProductPrice:
    """Цена товара с Saturn"""
    sku: str
    name: str
    price: float
    old_price: Optional[float]
    availability: str
    url: str
    parsed_at: datetime

# Тест создания объекта
try:
    result = ProductPrice(
        sku="103516",
        name="Тестовый товар",
        price=100.0,
        old_price=None,
        availability="Да",
        url="https://test.com",
        parsed_at=datetime.now()
    )
    print("✅ ProductPrice создан успешно")
    print(f"Артикул: {result.sku}")
    print(f"Цена: {result.price}")
except Exception as e:
    print(f"❌ Ошибка создания ProductPrice: {e}")

# Теперь попробуем импортировать из saturn_parser
try:
    from saturn_parser import ProductPrice as SPProductPrice
    
    result2 = SPProductPrice(
        sku="103516",
        name="Тестовый товар",
        price=100.0,
        old_price=None,
        availability="Да",
        url="https://test.com",
        parsed_at=datetime.now()
    )
    print("✅ ProductPrice из saturn_parser создан успешно")
except Exception as e:
    print(f"❌ Ошибка импорта из saturn_parser: {e}")
