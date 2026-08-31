"""
utils/logger.py
Configuração centralizada de logging para o LeadMap Pro.
Substitui todos os bare except: pass e print() de debug.
"""
import logging
import sys
import os


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "erros_robo.log")


class _ColorFormatter(logging.Formatter):
    """Formatter com cores ANSI para o terminal."""

    CORES = {
        logging.DEBUG:    "\033[94m",
        logging.INFO:     "\033[92m",
        logging.WARNING:  "\033[93m",
        logging.ERROR:    "\033[91m",
        logging.CRITICAL: "\033[95m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        cor = self.CORES.get(record.levelno, self.RESET)
        record.levelname = f"{cor}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado para o modulo informado.

    Uso:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Mensagem informativa")
        logger.error("Erro capturado", exc_info=True)
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVEL)
    console_formatter = _ColorFormatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger
