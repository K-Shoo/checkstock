"""Константы CheckStock: статусы, типы операций, метки."""

from enum import Enum


class OperationType(str, Enum):
    """Тип складской операции."""

    INBOUND = "INBOUND"
    FBS_RESERVE = "FBS_RESERVE"
    FBS_SHIP = "FBS_SHIP"
    FBS_CANCEL = "FBS_CANCEL"
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
    "TRANSFER": "Перемещение",
    "TRANSFER_RECEIVE": "Приёмка перемещения",
    "FBO_SHIP": "Отправка FBO",
    "FBO_RECEIVE": "Приёмка FBO",
}
