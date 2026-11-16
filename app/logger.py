"""Настройка логирования CheckStock."""

import logging

logger = logging.getLogger("checkstock")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)
logger.addHandler(handler)
