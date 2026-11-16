"""Бизнес-логика складских операций."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import InTransitKind, OperationType
from app.validators import ensure_active_warehouse, ensure_enough_stock
from app.models import (
    Discrepancy,
    InTransit,
    Operation,
    StockItem,
    StockLedger,
    Warehouse,
)


async def create_inbound(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    qty: int,
) -> Operation:
    """Оформить приход товара на склад."""
    if qty <= 0:
        raise ValueError("Количество должно быть положительным")
    warehouse = await ensure_active_warehouse(db, warehouse_id)

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == product_id,
                StockItem.warehouse_id == warehouse_id,
            )
        )
    ).scalar_one_or_none()

    if stock_item is None:
        stock_item = StockItem(
            product_id=product_id,
            warehouse_id=warehouse_id,
            qty_physical=0,
            qty_reserved_fbs=0,
        )
        db.add(stock_item)

    stock_item.qty_physical += qty

    operation = Operation(
        type=OperationType.INBOUND.value,
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty=qty,
    )
    db.add(operation)
    await db.flush()

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta_physical=qty,
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation


async def reserve_fbs(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    qty: int,
) -> Operation:
    """Зарезервировать товар под FBS на складе."""
    if qty <= 0:
        raise ValueError("Количество должно быть положительным")
    warehouse = await ensure_active_warehouse(db, warehouse_id)

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == product_id,
                StockItem.warehouse_id == warehouse_id,
            )
        )
    ).scalar_one_or_none()

    await ensure_enough_stock(
        db, stock_item, qty, warehouse.name, product_id
    )

    stock_item.qty_reserved_fbs += qty

    operation = Operation(
        type=OperationType.FBS_RESERVE.value,
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty=qty,
    )
    db.add(operation)
    await db.flush()

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta_reserved=qty,
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation


async def cancel_fbs(
    db: AsyncSession,
    operation_id: int,
) -> Operation:
    """Отменить резерв FBS."""
    operation = await db.get(Operation, operation_id)
    if operation is None or operation.type != OperationType.FBS_RESERVE.value:
        raise ValueError("Операция не найдена или не является резервом FBS")
    if operation.status != "PENDING":
        raise ValueError("Резерв уже обработан")

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == operation.product_id,
                StockItem.warehouse_id == operation.warehouse_id,
            )
        )
    ).scalar_one()

    if stock_item.qty_reserved_fbs < operation.qty:
        raise ValueError("Резерв меньше, чем нужно снять")

    stock_item.qty_reserved_fbs -= operation.qty
    operation.status = "CANCELLED"

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=operation.product_id,
            warehouse_id=operation.warehouse_id,
            delta_reserved=-operation.qty,
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation


async def ship_fbs(
    db: AsyncSession,
    operation_id: int,
) -> Operation:
    """Отправить заказ FBS: резерв снимается, товар едет к клиенту."""
    operation = await db.get(Operation, operation_id)
    if operation is None or operation.type != OperationType.FBS_RESERVE.value:
        raise ValueError("Операция не найдена или не является резервом FBS")
    if operation.status != "PENDING":
        raise ValueError("Резерв уже обработан")

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == operation.product_id,
                StockItem.warehouse_id == operation.warehouse_id,
            )
        )
    ).scalar_one()

    if stock_item.qty_reserved_fbs < operation.qty:
        raise ValueError("Резерв меньше, чем нужно списать")
    if stock_item.qty_physical < operation.qty:
        raise ValueError("Физического остатка не хватает")

    stock_item.qty_reserved_fbs -= operation.qty
    stock_item.qty_physical -= operation.qty
    operation.status = "CONFIRMED"

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=operation.product_id,
            warehouse_id=operation.warehouse_id,
            delta_physical=-operation.qty,
            delta_reserved=-operation.qty,
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation



async def create_transfer(
    db: AsyncSession,
    product_id: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    qty: int,
) -> Operation:
    """Отправить перемещение между ФФ: списать с источника."""
    if qty <= 0:
        raise ValueError("Количество должно быть положительным")
    if from_warehouse_id == to_warehouse_id:
        raise ValueError("Склады отправки и приёмки должны различаться")
    from_wh = await ensure_active_warehouse(db, from_warehouse_id)
    await ensure_active_warehouse(db, to_warehouse_id)

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == product_id,
                StockItem.warehouse_id == from_warehouse_id,
            )
        )
    ).scalar_one_or_none()

    await ensure_enough_stock(
        db, stock_item, qty, from_wh.name, product_id
    )

    stock_item.qty_physical -= qty

    operation = Operation(
        type=OperationType.TRANSFER.value,
        status="IN_TRANSIT",
        product_id=product_id,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        qty=qty,
    )
    db.add(operation)
    await db.flush()

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            delta_physical=-qty,
        )
    )
    db.add(
        InTransit(
            operation_id=operation.id,
            product_id=product_id,
            qty=qty,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            status="IN_TRANSIT",
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation


async def receive_transfer(
    db: AsyncSession,
    operation_id: int,
    fact_qty: int | None = None,
    comment: str | None = None,
) -> Operation:
    """Принять перемещение. Если факт расходится с отправкой — акт расхождения."""
    operation = await db.get(Operation, operation_id)
    if operation is None or operation.type != OperationType.TRANSFER.value:
        raise ValueError("Операция не найдена или не является перемещением")
    if operation.status != "IN_TRANSIT":
        raise ValueError("Перемещение уже принято или отменено")

    in_transit = (
        await db.execute(
            select(InTransit).where(
                InTransit.operation_id == operation_id,
                InTransit.status == "IN_TRANSIT",
            )
        )
    ).scalar_one_or_none()
    if in_transit is None:
        raise ValueError("Запись о товаре в пути не найдена")

    if fact_qty is None:
        fact_qty = operation.qty
    if fact_qty < 0:
        raise ValueError("Фактическое количество не может быть отрицательным")

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == operation.product_id,
                StockItem.warehouse_id == operation.to_warehouse_id,
            )
        )
    ).scalar_one_or_none()

    if stock_item is None:
        stock_item = StockItem(
            product_id=operation.product_id,
            warehouse_id=operation.to_warehouse_id,
            qty_physical=0,
            qty_reserved_fbs=0,
        )
        db.add(stock_item)

    stock_item.qty_physical += fact_qty
    in_transit.status = "RECEIVED"
    operation.status = "RECEIVED"

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=operation.product_id,
            warehouse_id=operation.to_warehouse_id,
            delta_physical=fact_qty,
        )
    )

    if fact_qty != operation.qty:
        db.add(
            Discrepancy(
                operation_id=operation.id,
                sent_qty=operation.qty,
                fact_qty=fact_qty,
                delta=fact_qty - operation.qty,
                comment=comment,
            )
        )

    await db.commit()
    await db.refresh(operation)
    return operation


async def create_fbo_ship(
    db: AsyncSession,
    product_id: int,
    warehouse_id: int,
    qty: int,
) -> Operation:
    """Отправить товар на склад маркетплейса (FBO)."""
    if qty <= 0:
        raise ValueError("Количество должно быть положительным")
    warehouse = await ensure_active_warehouse(db, warehouse_id)

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == product_id,
                StockItem.warehouse_id == warehouse_id,
            )
        )
    ).scalar_one_or_none()

    await ensure_enough_stock(
        db, stock_item, qty, warehouse.name, product_id
    )

    stock_item.qty_physical -= qty

    operation = Operation(
        type=OperationType.FBO_SHIP.value,
        status="IN_TRANSIT",
        product_id=product_id,
        warehouse_id=warehouse_id,
        qty=qty,
    )
    db.add(operation)
    await db.flush()

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            delta_physical=-qty,
        )
    )
    db.add(
        InTransit(
            operation_id=operation.id,
            product_id=product_id,
            qty=qty,
            kind=InTransitKind.FBO_TO_MARKETPLACE.value,
            from_warehouse_id=warehouse_id,
            to_warehouse_id=None,
            status="IN_TRANSIT",
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation


async def receive_fbo(
    db: AsyncSession,
    operation_id: int,
) -> Operation:
    """Подтвердить приёмку товара на складе маркетплейса."""
    operation = await db.get(Operation, operation_id)
    if operation is None or operation.type != OperationType.FBO_SHIP.value:
        raise ValueError("Операция не найдена или не является отправкой FBO")
    if operation.status != "IN_TRANSIT":
        raise ValueError("Отправка уже принята или отменена")

    in_transit = (
        await db.execute(
            select(InTransit).where(
                InTransit.operation_id == operation_id,
                InTransit.status == "IN_TRANSIT",
            )
        )
    ).scalar_one_or_none()
    if in_transit is None:
        raise ValueError("Запись о товаре в пути не найдена")

    in_transit.status = "RECEIVED"
    operation.status = "RECEIVED"

    await db.commit()
    await db.refresh(operation)
    return operation


async def create_warehouse(
    db: AsyncSession,
    name: str,
) -> Warehouse:
    """Создать новый склад."""
    if not name.strip():
        raise ValueError("Название склада не может быть пустым")

    existing = (
        await db.execute(
            select(Warehouse).where(Warehouse.name == name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Склад с таким названием уже существует")

    warehouse = Warehouse(name=name.strip())
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


async def rename_warehouse(
    db: AsyncSession,
    warehouse_id: int,
    new_name: str,
) -> Warehouse:
    """Переименовать склад."""
    if not new_name.strip():
        raise ValueError("Название склада не может быть пустым")

    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise ValueError("Склад не найден")

    existing = (
        await db.execute(
            select(Warehouse).where(
                Warehouse.name == new_name,
                Warehouse.id != warehouse_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("Склад с таким названием уже существует")

    warehouse.name = new_name.strip()
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


async def deactivate_warehouse(
    db: AsyncSession,
    warehouse_id: int,
) -> Warehouse:
    """Удалить склад, если на нём нет остатков и в пути."""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise ValueError("Склад не найден")

    stock = (
        await db.execute(
            select(StockItem).where(
                StockItem.warehouse_id == warehouse_id,
                StockItem.qty_physical > 0,
            )
        )
    ).scalars().all()
    if stock:
        total = sum(item.qty_physical for item in stock)
        raise ValueError(
            f"На складе осталось {total} ед. товара. "
            "Удаление невозможно, пока остаток не обнулён."
        )

    in_transit_from = (
        await db.execute(
            select(InTransit).where(
                InTransit.from_warehouse_id == warehouse_id,
                InTransit.status == "IN_TRANSIT",
            )
        )
    ).scalars().all()
    if in_transit_from:
        raise ValueError(
            "Со склада отправлен товар (в пути). "
            "Удаление невозможно, пока перемещение не принято."
        )

    in_transit_to = (
        await db.execute(
            select(InTransit).where(
                InTransit.to_warehouse_id == warehouse_id,
                InTransit.status == "IN_TRANSIT",
            )
        )
    ).scalars().all()
    if in_transit_to:
        raise ValueError(
            "На склад едет товар (в пути). "
            "Удаление невозможно, пока перемещение не принято."
        )

    warehouse.is_active = False
    await db.commit()
    await db.refresh(warehouse)
    return warehouse




async def restore_warehouse(
    db: AsyncSession,
    warehouse_id: int,
) -> Warehouse:
    """Восстановить ранее удалённый склад."""
    warehouse = await db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise ValueError("Склад не найден")
    if warehouse.is_active:
        raise ValueError("Склад уже активен")

    existing = (
        await db.execute(
            select(Warehouse).where(
                Warehouse.name == warehouse.name,
                Warehouse.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError(
            "Активный склад с таким названием уже существует."
        )

    warehouse.is_active = True
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


async def cancel_transfer(
    db: AsyncSession,
    operation_id: int,
) -> Operation:
    """Отменить перемещение: вернуть товар на склад-источник."""
    operation = await db.get(Operation, operation_id)
    if operation is None or operation.type != OperationType.TRANSFER.value:
        raise ValueError("Операция не найдена или не является перемещением")
    if operation.status != "IN_TRANSIT":
        raise ValueError("Перемещение уже принято или отменено")

    in_transit = (
        await db.execute(
            select(InTransit).where(
                InTransit.operation_id == operation_id,
                InTransit.status == "IN_TRANSIT",
            )
        )
    ).scalar_one_or_none()
    if in_transit is None:
        raise ValueError("Запись о товаре в пути не найдена")

    stock_item = (
        await db.execute(
            select(StockItem).where(
                StockItem.product_id == operation.product_id,
                StockItem.warehouse_id == operation.from_warehouse_id,
            )
        )
    ).scalar_one_or_none()

    if stock_item is None:
        stock_item = StockItem(
            product_id=operation.product_id,
            warehouse_id=operation.from_warehouse_id,
            qty_physical=0,
            qty_reserved_fbs=0,
        )
        db.add(stock_item)

    stock_item.qty_physical += operation.qty

    in_transit.status = "CANCELLED"
    operation.status = "CANCELLED"

    db.add(
        StockLedger(
            operation_id=operation.id,
            product_id=operation.product_id,
            warehouse_id=operation.from_warehouse_id,
            delta_physical=operation.qty,
        )
    )
    await db.commit()
    await db.refresh(operation)
    return operation
