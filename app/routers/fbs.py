"""Резерв, отправка и отмена FBS."""

from fastapi import APIRouter, Depends, Form, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Product, Warehouse
from app.schemas import FbsReserveForm
from app.services import (
    cancel_fbs,
    deliver_fbs,
    reserve_fbs,
    ship_fbs,
)
from app.logger import logger

router = APIRouter(prefix="/fbs", tags=["FBS"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Форма резерва FBS",
    description="Форма для резервирования товара под заказы FBS.",
)
async def fbs_form(
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
        "fbs.html",
        {
            "request": request,
            "products": products,
            "warehouses": warehouses,
            "error": error,
        },
    )


@router.post(
    "/reserve",
    summary="Зарезервировать под FBS",
    description=(
        "Блокирует товар на складе под заказ FBS. "
        "Увеличивает `qty_reserved_fbs`, доступный остаток уменьшается."
    ),
    responses={303: {"description": "Резерв создан, редирект на главную"}},
)
async def fbs_reserve(
    form: FbsReserveForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await reserve_fbs(
            db, form.product_id, form.warehouse_id, form.qty
        )
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/fbs?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post(
    "/{operation_id}/ship",
    summary="Отправить заказ FBS",
    description=(
        "Списывает физический остаток и снимает резерв. "
        "Товар считается отправленным клиенту."
    ),
    responses={303: {"description": "Заказ отправлен, редирект на главную"}},
)
async def fbs_ship(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await ship_fbs(db, operation_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post(
    "/{operation_id}/cancel",
    summary="Отменить резерв FBS",
    description="Снимает резерв FBS, товар снова становится доступным.",
    responses={303: {"description": "Резерв отменён, редирект на главную"}},
)
async def fbs_cancel(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await cancel_fbs(db, operation_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post(
    "/{operation_id}/deliver",
    summary="Подтвердить доставку FBS",
    description="Закрывает заказ: списывает физический остаток.",
    responses={303: {"description": "Доставка подтверждена, редирект на главную"}},
)
async def fbs_deliver(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await deliver_fbs(db, operation_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)
