"""Configuracao centralizada de logs da automacao."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import PROJECT_DIR


# O diretório é criado automaticamente na primeira execução.
LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "dashboard.log"


def configurar_logger() -> logging.Logger:
    """Cria um logger UTF-8 com rotacao e evita handlers duplicados."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("dashboard_gerencial")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Evita adicionar o mesmo handler quando o módulo é importado mais de uma vez.
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger
