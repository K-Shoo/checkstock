"""Бизнес-валидаторы CheckStock."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Operation, StockItem, Warehouse


async def ensure_active_warehouse(
    db: AsyncSession,
    warehouse_id: int,
) -> Warehouse:
    """Проверить, что склад существует и активен."""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise ValueError("Склад удалён или не существует")
    return warehouse


async def ensure_enough_stock(
    db: AsyncSession,
    stock_item: StockItem | None,
    qty: int,
    warehouse_name: str,
    product_id: int,
) -> None:
    """Проверить остаток; если не хватает — подсказать, где есть."""
    if stock_item is not None and stock_item.qty_available >= qty:
        return

    available = stock_item.qty_available if stock_item else 0

    others = (
        await db.execute(
            select(StockItem, Warehouse)
            .join(Warehouse, Warehouse.id == StockItem.warehouse_id)
            .where(
                StockItem.product_id == product_id,
                StockItem.warehouse_id != (stock_item.warehouse_id if stock_item else 0),
                StockItem.qty_physical > 0,
                Warehouse.is_active.is_(True),
            )
        )
    ).all()

    hints = [
        f"«{wh.name}» — {item.qty_available} шт."
        for item, wh in others
        if item.qty_available > 0
    ]

    msg = (
        f"На складе «{warehouse_name}» доступно {available} шт., "
        f"нужно {qty}."
    )
    if hints:
        msg += " Есть на: " + "; ".join(hints) + "."
    raise ValueError(msg)


def ensure_operation_status(
    operation: Operation | None,
    expected_type: str,
    expected_status: str,
    error: str,
) -> None:
    """Проверить тип и статус операции."""
    if operation is None or operation.type != expected_type:
        raise ValueError("Операция не найдена или имеет неверный тип")
    if operation.status != expected_status:
        raise ValueError(error)
