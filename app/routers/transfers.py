"""Перемещения между складами ФФ."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Operation, Product, Warehouse
from app.schemas import TransferForm
from app.services import cancel_transfer, create_transfer, receive_transfer

router = APIRouter(prefix="/transfers", tags=["Перемещения"])
templates = Jinja2Templates(directory="app/templates")


@router.get(
    "",
    response_class=HTMLResponse,
    summary="Форма перемещения",
    description="Форма для отправки товара с одного склада ФФ на другой.",
)
async def transfer_form(
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
        "transfer.html",
        {
            "request": request,
            "products": products,
            "warehouses": warehouses,
            "error": error,
        },
    )


@router.post(
    "/send",
    summary="Отправить перемещение",
    description=(
        "Списывает товар со склада-источника. "
        "Товар переходит в статус «В пути между ФФ»."
    ),
    responses={303: {"description": "Перемещение отправлено, редирект на главную"}},
)
async def transfer_send(
    form: TransferForm = Form(),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await create_transfer(
            db,
            form.product_id,
            form.from_warehouse_id,
            form.to_warehouse_id,
            form.qty,
        )
    except ValueError as exc:
        return RedirectResponse(url=f"/transfers?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@router.get(
    "/{operation_id}/receive",
    response_class=HTMLResponse,
    summary="Форма приёмки перемещения",
    description="Форма приёмки: можно указать фактическое количество.",
)
async def transfer_receive_form(
    request: Request,
    operation_id: int,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    operation = (
        await db.execute(
            select(Operation)
            .options(
                selectinload(Operation.product),
                selectinload(Operation.from_warehouse),
                selectinload(Operation.to_warehouse),
            )
            .where(Operation.id == operation_id)
        )
    ).scalar_one_or_none()
    if operation is None:
        return RedirectResponse(url="/?error=Операция не найдена", status_code=303)
    return templates.TemplateResponse(
        "receive.html",
        {"request": request, "operation": operation, "error": error},
    )


@router.post(
    "/{operation_id}/receive",
    summary="Принять перемещение",
    description=(
        "Зачисляет фактически принятое количество на склад-назначение. "
        "Если факт расходится с отправкой — создаётся акт расхождения."
    ),
    responses={303: {"description": "Перемещение принято, редирект на главную"}},
)
async def transfer_receive(
    operation_id: int,
    fact_qty: int | None = Form(None),
    comment: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await receive_transfer(db, operation_id, fact_qty, comment)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/transfers/{operation_id}/receive?error={exc}",
            status_code=303,
        )
    return RedirectResponse(url="/", status_code=303)


@router.post(
    "/{operation_id}/cancel",
    summary="Отменить перемещение",
    description=(
        "Возвращает товар на склад-источник. "
        "Доступно только для перемещений в статусе «В пути»."
    ),
    responses={303: {"description": "Перемещение отменено, редирект на главную"}},
)
async def transfer_cancel(
    operation_id: int,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    try:
        await cancel_transfer(db, operation_id)
    except ValueError as exc:
        return RedirectResponse(url=f"/?error={exc}", status_code=303)
    return RedirectResponse(url="/", status_code=303)
