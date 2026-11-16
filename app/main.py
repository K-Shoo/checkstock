"""Точка входа FastAPI-приложения CheckStock."""

from fastapi import FastAPI, Response

from app.routers import (
    fbo,
    fbs,
    inbound,
    products,
    stock,
    transfers,
    warehouses,
)

app = FastAPI(
    title="CheckStock",
    description=(
        "Прототип учёта товара на складах фулфилмента (ФФ).\n\n"
        "Позволяет видеть, где находится товар: физически на складе, "
        "в резерве FBS, в пути между ФФ, на складе маркетплейса "
        "(FBO) или у клиента (FBS).\n\n"
        "**Операции:** приход, резерв/отправка/отмена FBS, "
        "перемещение между ФФ, отправка/приёмка FBO.\n\n"
        "**Склады:** добавление, переименование, удаление (с сохранением "
        "истории), восстановление."
    ),
    version="0.1.0",
)

app.include_router(stock.router)
app.include_router(inbound.router)
app.include_router(fbs.router)
app.include_router(transfers.router)
app.include_router(fbo.router)
app.include_router(warehouses.router)
app.include_router(products.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Заглушка для favicon, чтобы браузер не получал 404."""
    return Response(status_code=204)
