"""Заполнение базы тестовыми данными из ТЗ."""

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Product, StockItem, Warehouse

STOCK = {
    "SKU-101": {"Север": 10, "Юг": 6},
    "SKU-102": {"Север": 5, "Юг": 0},
    "SKU-103": {"Север": 0, "Юг": 4},
}

PRODUCTS = [
    ("SKU-101", "Органайзер"),
    ("SKU-102", "Контейнер"),
    ("SKU-103", "Корзина"),
]


async def main() -> None:
    """Создать склады, товары и остатки, если их ещё нет."""
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(Product).limit(1))
        ).scalar_one_or_none()
        if existing is not None:
            print("Данные уже есть, сид пропущен")
            return

        north = Warehouse(name="Север")
        south = Warehouse(name="Юг")
        db.add_all([north, south])
        await db.flush()

        products = [Product(sku=sku, name=name) for sku, name in PRODUCTS]
        db.add_all(products)
        await db.flush()

        warehouses = {"Север": north, "Юг": south}
        for product in products:
            for wh_name, qty in STOCK[product.sku].items():
                db.add(
                    StockItem(
                        product_id=product.id,
                        warehouse_id=warehouses[wh_name].id,
                        qty_physical=qty,
                        qty_reserved_fbs=0,
                    )
                )
        await db.commit()
        print("Сид загружен")


if __name__ == "__main__":
    asyncio.run(main())
