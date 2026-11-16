"""Отправка FBO на склад маркетплейса."""

from fastapi import APIRouter, Depends, Form, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Product, Warehouse
from app.schemas import FboSendForm
from app.services import create_fbo_ship, receive_fbo
from app.logger import logger

router = APIRouter(prefix="/fbo", tags=["FBO"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Форма отправки FBO",
    description="Форма для отправки товара на склад маркетплейса.",
)
async def fbo_form(
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
        "fbo.html",
        {
            "request": request,
            "products": products,
            "warehouses": warehouses,
            "error": error,
        },
    )


@router.post(
    "/send",
    summary="Отправить FBO",
    description=(
        "Списывает товар со склада ФФ. "
        "Товар переходит в статус «В пути на склад маркетплейса»."
    ),
    responses={303: {"description": "FBO отправлен, редирект на главную"}},
)
async def fbo_send(
    form: FboSendForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await create_fbo_ship(
            db, form.product_id, form.warehouse_id, form.qty
        )
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/fbo?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.post(
    "/{operation_id}/receive",
    summary="Принять FBO",
    description=(
        "Подтверждает приёмку товара на складе маркетплейса. "
        "На склад ФФ ничего не зачисляется."
    ),
    responses={303: {"description": "FBO принят, редирект на главную"}},
)
async def fbo_receive(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await receive_fbo(db, operation_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)
