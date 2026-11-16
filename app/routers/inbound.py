"""Приход товара на склад."""

from fastapi import APIRouter, Depends, Form, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Product, Warehouse
from app.schemas import InboundForm
from app.services import create_inbound

router = APIRouter(prefix="/inbound", tags=["Приход"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Форма прихода",
    description="Форма для оформления прихода товара на склад.",
)
async def inbound_form(
    request: Request,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    products = (
        await db.execute(select(Product).order_by(Product.sku))
    ).scalars().all()
    warehouses = (
        await db.execute(
            select(Warehouse)
            .where(Warehouse.is_active.is_(True))
            .order_by(Warehouse.id)
        )
    ).scalars().all()
    return templates.TemplateResponse(
        "inbound.html",
        {
            "request": request,
            "products": products,
            "warehouses": warehouses,
            "error": error,
        },
    )


@router.post(
    "",
    summary="Оформить приход",
    description=(
        "Увеличивает физический остаток товара на выбранном складе. "
        "Создаёт операцию типа `INBOUND` и запись в журнале остатков."
    ),
    responses={303: {"description": "Приход оформлен, редирект на главную"}},
)
async def inbound_submit(
    form: InboundForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await create_inbound(
            db, form.product_id, form.warehouse_id, form.qty
        )
    except ValueError as exc:
        return RedirectResponse(url=f"/inbound?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)
