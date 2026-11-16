"""Pydantic-схемы для форм CheckStock."""

from pydantic import BaseModel, Field

from app.constants import (
    MAX_COMMENT_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
    MAX_SKU_LENGTH,
    MAX_WAREHOUSE_NAME_LENGTH,
    MIN_QTY,
)


class InboundForm(BaseModel):
    """Приход товара на склад."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., ge=MIN_QTY, description="Количество единиц (больше 0)")


class FbsReserveForm(BaseModel):
    """Резерв товара под FBS."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., ge=MIN_QTY, description="Количество единиц (больше 0)")


class TransferForm(BaseModel):
    """Перемещение товара между ФФ."""

    product_id: int = Field(..., description="ID товара")
    from_warehouse_id: int = Field(..., description="ID склада-источника")
    to_warehouse_id: int = Field(..., description="ID склада-назначения")
    qty: int = Field(..., ge=MIN_QTY, description="Количество единиц (больше 0)")


class FboSendForm(BaseModel):
    """Отправка товара на склад маркетплейса."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., ge=MIN_QTY, description="Количество единиц (больше 0)")


class WarehouseCreateForm(BaseModel):
    """Создание склада."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_WAREHOUSE_NAME_LENGTH,
        description="Название склада (уникальное)",
    )


class WarehouseRenameForm(BaseModel):
    """Переименование склада."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_WAREHOUSE_NAME_LENGTH,
        description="Новое название (уникальное)",
    )


class ProductCreateForm(BaseModel):
    """Создание товара. Артикул генерируется автоматически."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_PRODUCT_NAME_LENGTH,
        description="Название товара",
    )


class ProductRenameForm(BaseModel):
    """Переименование товара."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_PRODUCT_NAME_LENGTH,
        description="Новое название",
    )
