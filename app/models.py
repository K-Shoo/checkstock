"""SQLAlchemy-модели CheckStock."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import STATUS_LABELS, TYPE_LABELS
from app.db import Base


def utcnow() -> datetime:
    """Текущее время в UTC."""
    return datetime.now(timezone.utc)


class Product(Base):
    """Товар (артикул)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))

    stock_items: Mapped[list["StockItem"]] = relationship(
        back_populates="product",
    )


class Warehouse(Base):
    """Склад фулфилмента (ФФ)."""

    __tablename__ = "warehouses"
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="1",
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

    stock_items: Mapped[list["StockItem"]] = relationship(
        back_populates="warehouse",
    )


class StockItem(Base):
    """Остаток конкретного товара на конкретном складе."""

    __tablename__ = "stock_items"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_stock_product_warehouse",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    qty_physical: Mapped[int] = mapped_column(Integer, default=0)
    qty_reserved_fbs: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="stock_items")
    warehouse: Mapped[Warehouse] = relationship(back_populates="stock_items")

    @property
    def qty_available(self) -> int:
        return self.qty_physical - self.qty_reserved_fbs


class Operation(Base):
    """Складская операция (движение товара)."""

    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        server_default="PENDING",
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True,
    )
    from_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True,
    )
    to_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True,
    )
    qty: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    product: Mapped[Product] = relationship()
    warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[warehouse_id],
    )
    from_warehouse: Mapped[Warehouse | None] = relationship(
        foreign_keys=[from_warehouse_id],
    )
    to_warehouse: Mapped[Warehouse | None] = relationship(
        foreign_keys=[to_warehouse_id],
    )

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.type, self.type)


class InTransit(Base):
    """Товар в пути."""

    __tablename__ = "in_transit"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(
        String(32),
        default="BETWEEN_FF",
        server_default="BETWEEN_FF",
    )
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    to_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="IN_TRANSIT",
        server_default="IN_TRANSIT",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    product: Mapped[Product] = relationship()
    from_warehouse: Mapped[Warehouse] = relationship(
        foreign_keys=[from_warehouse_id],
    )
    to_warehouse: Mapped[Warehouse | None] = relationship(
        foreign_keys=[to_warehouse_id],
    )


class StockLedger(Base):
    """Журнал изменений остатков."""

    __tablename__ = "stock_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    delta_physical: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    delta_reserved: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )


class Discrepancy(Base):
    """Акт расхождения при приёмке перемещения."""

    __tablename__ = "discrepancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    operation_id: Mapped[int] = mapped_column(ForeignKey("operations.id"))
    sent_qty: Mapped[int] = mapped_column(Integer)
    fact_qty: Mapped[int] = mapped_column(Integer)
    delta: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    operation: Mapped["Operation"] = relationship()
