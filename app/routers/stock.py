"""Экран остатков и история операций."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    DISCREPANCIES_LIMIT,
    OPERATIONS_HISTORY_LIMIT,
)
from app.db import get_db
from app.models import (
    Discrepancy,
    MarketplaceStock,
    InTransit,
    Operation,
    Product,
    StockItem,
    Warehouse,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Экран остатков",
    description=(
        "Главная страница: остатки по активным складам, "
        "товары в пути (между ФФ и на маркетплейс), "
        "блок «Где числится товар» (включая архивные склады) "
        "и история последних операций."
    ),
    tags=["Остатки"],
)
async def index(
    request: Request,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Показать остатки, товар в пути и последние операции."""
    products = (
        await db.execute(
            select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.sku)
        )
    ).scalars().all()
    warehouses = (
        await db.execute(
            select(Warehouse)
            .where(Warehouse.is_active.is_(True))
            .order_by(Warehouse.id)
        )
    ).scalars().all()
    all_warehouses = (
        await db.execute(select(Warehouse).order_by(Warehouse.id))
    ).scalars().all()
    stock_items = (await db.execute(select(StockItem))).scalars().all()
    operations = (
        await db.execute(
            select(Operation).order_by(Operation.created_at.desc()).limit(OPERATIONS_HISTORY_LIMIT)
        )
    ).scalars().all()
    in_transit = (
        await db.execute(
            select(InTransit).where(InTransit.status == "IN_TRANSIT")
        )
    ).scalars().all()
    marketplace_stock = (
        await db.execute(
            select(MarketplaceStock)
            .options(selectinload(MarketplaceStock.product))
            .where(MarketplaceStock.qty > 0)
            .order_by(MarketplaceStock.product_id)
        )
    ).scalars().all()
    discrepancies = (
        await db.execute(
            select(Discrepancy)
            .options(
                selectinload(Discrepancy.operation).selectinload(
                    Operation.product
                ),
                selectinload(Discrepancy.operation).selectinload(
                    Operation.from_warehouse
                ),
                selectinload(Discrepancy.operation).selectinload(
                    Operation.to_warehouse
                ),
            )
            .order_by(Discrepancy.created_at.desc())
            .limit(OPERATIONS_HISTORY_LIMIT)
        )
    ).scalars().all()

    stock_map = {
        (item.product_id, item.warehouse_id): item for item in stock_items
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "warehouses": warehouses,
            "all_warehouses": all_warehouses,
            "stock_map": stock_map,
            "operations": operations,
            "in_transit": in_transit,
            "marketplace_stock": marketplace_stock,
            "discrepancies": discrepancies,
            "error": error,
        },
    )
