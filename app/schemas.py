"""Pydantic-схемы для форм CheckStock."""

from pydantic import BaseModel, Field


class InboundForm(BaseModel):
    """Приход товара на склад."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., gt=0, description="Количество единиц (больше 0)")


class FbsReserveForm(BaseModel):
    """Резерв товара под FBS."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., gt=0, description="Количество единиц (больше 0)")


class TransferForm(BaseModel):
    """Перемещение товара между ФФ."""

    product_id: int = Field(..., description="ID товара")
    from_warehouse_id: int = Field(..., description="ID склада-источника")
    to_warehouse_id: int = Field(..., description="ID склада-назначения")
    qty: int = Field(..., gt=0, description="Количество единиц (больше 0)")


class FboSendForm(BaseModel):
    """Отправка товара на склад маркетплейса."""

    product_id: int = Field(..., description="ID товара")
    warehouse_id: int = Field(..., description="ID склада")
    qty: int = Field(..., gt=0, description="Количество единиц (больше 0)")


class WarehouseCreateForm(BaseModel):
    """Создание склада."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Название склада (уникальное)",
    )


class WarehouseRenameForm(BaseModel):
    """Переименование склада."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Новое название (уникальное)",
    )
