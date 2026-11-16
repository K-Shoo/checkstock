"""Управление складами ФФ."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Warehouse
from app.schemas import WarehouseCreateForm, WarehouseRenameForm
from app.services import (
    create_warehouse,
    deactivate_warehouse,
    rename_warehouse,
    restore_warehouse,
)
from app.logger import logger

router = APIRouter(prefix="/warehouses", tags=["Склады"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Список складов",
    description="Список всех складов ФФ, включая архивные.",
)
async def warehouses_list(
    request: Request,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    warehouses = (
        await db.execute(select(Warehouse).order_by(Warehouse.id))
    ).scalars().all()
    return templates.TemplateResponse(
        "warehouses.html",
        {"request": request, "warehouses": warehouses, "error": error},
    )


@router.post(
    "/create",
    summary="Создать склад",
    description="Добавляет новый склад ФФ. Название должно быть уникальным.",
    responses={303: {"description": "Склад создан, редирект к списку"}},
)
async def warehouses_create(
    form: WarehouseCreateForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await create_warehouse(db, form.name)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/warehouses?error={exc}", status_code=303)
    return RedirectResponse(url="/warehouses", status_code=303)


@router.post(
    "/{warehouse_id}/rename",
    summary="Переименовать склад",
    description="Меняет название склада. Новое имя должно быть уникальным.",
    responses={303: {"description": "Склад переименован, редирект к списку"}},
)
async def warehouses_rename(
    warehouse_id: int,
    form: WarehouseRenameForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await rename_warehouse(db, warehouse_id, form.name)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/warehouses?error={exc}", status_code=303)
    return RedirectResponse(url="/warehouses", status_code=303)


@router.post(
    "/{warehouse_id}/delete",
    summary="Удалить склад",
    description=(
        "Помечает склад как архивный (soft-delete). "
        "Удаление невозможно, если на складе есть остаток или "
        "если с него/на него едет товар."
    ),
    responses={303: {"description": "Склад удалён, редирект к списку"}},
)
async def warehouses_delete(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await deactivate_warehouse(db, warehouse_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/warehouses?error={exc}", status_code=303)
    return RedirectResponse(url="/warehouses", status_code=303)


@router.post(
    "/{warehouse_id}/restore",
    summary="Восстановить склад",
    description="Возвращает архивный склад в активные.",
    responses={303: {"description": "Склад восстановлен, редирект к списку"}},
)
async def warehouses_restore(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await restore_warehouse(db, warehouse_id)
    except ValueError as exc:
        logger.warning("Ошибка: %s", exc)
        return RedirectResponse(url=f"/warehouses?error={exc}", status_code=303)
    return RedirectResponse(url="/warehouses", status_code=303)
