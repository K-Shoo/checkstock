"""Константы CheckStock: статусы, типы операций, метки."""

from enum import Enum


class OperationType(str, Enum):
    """Тип складской операции.

    FBS_SHIP, FBS_CANCEL, TRANSFER_RECEIVE, FBO_RECEIVE
    не создаются как отдельные операции: отправка/приёмка
    меняет статус исходной операции. Оставлены как справочник
    для будущего раздельного учёта.
    """

    INBOUND = "INBOUND"
    FBS_RESERVE = "FBS_RESERVE"
    FBS_SHIP = "FBS_SHIP"
    FBS_CANCEL = "FBS_CANCEL"
    FBS_DELIVERED = "FBS_DELIVERED"
    TRANSFER = "TRANSFER"
    TRANSFER_RECEIVE = "TRANSFER_RECEIVE"
    FBO_SHIP = "FBO_SHIP"
    FBO_RECEIVE = "FBO_RECEIVE"


class InTransitKind(str, Enum):
    """Куда едет товар."""

    BETWEEN_FF = "BETWEEN_FF"
    FBO_TO_MARKETPLACE = "FBO_TO_MARKETPLACE"
    FBS_TO_CLIENT = "FBS_TO_CLIENT"


STATUS_LABELS = {
    "PENDING": "В ожидании",
    "CONFIRMED": "Подтверждено",
    "CANCELLED": "Отменено",
    "IN_TRANSIT": "В пути",
    "RECEIVED": "Принято",
}

TYPE_LABELS = {
    "INBOUND": "Приход",
    "FBS_RESERVE": "Резерв FBS",
    "FBS_SHIP": "Отправка FBS",
    "FBS_CANCEL": "Отмена FBS",
    "FBS_DELIVERED": "Доставка FBS",
    "TRANSFER": "Перемещение",
    "TRANSFER_RECEIVE": "Приёмка перемещения",
    "FBO_SHIP": "Отправка FBO",
    "FBO_RECEIVE": "Приёмка FBO",
}


# --- Числовые константы ---

SKU_START_NUMBER = 101
SKU_PREFIX = "SKU-"

OPERATIONS_HISTORY_LIMIT = 20
DISCREPANCIES_LIMIT = 20

MAX_SKU_LENGTH = 64
MAX_PRODUCT_NAME_LENGTH = 255
MAX_WAREHOUSE_NAME_LENGTH = 120
MAX_COMMENT_LENGTH = 500

MIN_QTY = 1
