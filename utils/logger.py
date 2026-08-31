"""
utils/logger.py
Configuracao centralizada de logging para o LeadMap Pro.
Substitui todos os bare except: pass e print() de debug.
Totalmente tolerante a montagens de volume Docker.
"""
import logging
import sys
import os


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def _get_log_file_path() -> str:
    """Retorna caminho seguro do arquivo de log, tolerando pastas montadas pelo Docker."""
    raw_path = os.getenv("LOG_FILE", "logs/erros_robo.log")
    
    if os.path.isdir(raw_path):
        return os.path.join(raw_path, "erros_robo.log")

    dir_name = os.path.dirname(raw_path)
    if dir_name:
        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception:
            pass
    return raw_path


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
    logger.addHandler(console_handler)

    # File handler protegido contra erros de permissao ou diretorios
    try:
        log_path = _get_log_file_path()
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.WARNING)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        console_handler.stream.write(f"[WARN] Nao foi possivel criar FileHandler para logs: {e}\n")

    logger.propagate = False
    return logger
