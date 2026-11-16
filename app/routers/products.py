"""Управление товарами."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.logger import logger
from app.models import Product
from app.schemas import ProductCreateForm, ProductRenameForm
from app.services import (
    create_product,
    deactivate_product,
    rename_product,
    restore_product,
)

router = APIRouter(prefix="/products", tags=["Товары"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Список товаров",
    description="Список всех товаров, включая удалённые.",
)
async def products_list(
    request: Request,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    products = (
        await db.execute(select(Product).order_by(Product.sku))
    ).scalars().all()
    return templates.TemplateResponse(
        "products.html",
        {"request": request, "products": products, "error": error},
    )


@router.post(
    "/create",
    summary="Создать товар",
    description="Добавляет новый товар. Артикул можно не указывать — сгенерируется.",
    responses={303: {"description": "Товар создан, редирект к списку"}},
)
async def products_create(
    form: ProductCreateForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await create_product(db, form.name)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/products?error={exc}", status_code=303)
    return RedirectResponse(url="/products", status_code=303)


@router.post(
    "/{product_id}/rename",
    summary="Переименовать товар",
    description="Меняет название товара.",
    responses={303: {"description": "Товар переименован, редирект к списку"}},
)
async def products_rename(
    product_id: int,
    form: ProductRenameForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await rename_product(db, product_id, form.name)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/products?error={exc}", status_code=303)
    return RedirectResponse(url="/products", status_code=303)


@router.post(
    "/{product_id}/delete",
    summary="Удалить товар",
    description=(
        "Помечает товар как удалённый (soft-delete). "
        "Удаление невозможно, если на складах есть остаток "
        "или товар в пути."
    ),
    responses={303: {"description": "Товар удалён, редирект к списку"}},
)
async def products_delete(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await deactivate_product(db, product_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/products?error={exc}", status_code=303)
    return RedirectResponse(url="/products", status_code=303)


@router.post(
    "/{product_id}/restore",
    summary="Восстановить товар",
    description="Возвращает удалённый товар в активные.",
    responses={303: {"description": "Товар восстановлен, редирект к списку"}},
)
async def products_restore(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await restore_product(db, product_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/products?error={exc}", status_code=303)
    return RedirectResponse(url="/products", status_code=303)
