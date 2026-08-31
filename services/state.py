"""
services/state.py
Estado global do pipeline — thread-safe, isolado por sessão.
"""
import queue
import threading
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


class ResultadosThread:
    """
    Lista thread-safe para armazenar resultados finais.
    Substitui a lista nua 'resultados_finais = []' que sofria race conditions.
    """
    def __init__(self):
        self._data: list[dict] = []
        self._lock = threading.Lock()

    def append(self, item: dict) -> None:
        with self._lock:
            self._data.append(item)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def copy(self) -> list[dict]:
        """Retorna uma cópia da lista para leitura segura."""
        with self._lock:
            return list(self._data)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def __iter__(self):
        # Itera sobre uma cópia para evitar deadlocks
        return iter(self.copy())

    def __getitem__(self, index):
        with self._lock:
            return self._data[index]

    def __bool__(self) -> bool:
        with self._lock:
            return bool(self._data)


class PipelineState:
    """
    Encapsula todo o estado de pipeline de UMA sessão de usuário.
    Cada usuário tem sua própria instância — sem compartilhamento acidental.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id

        # Filas de comunicação entre os robôs
        self.fila_raw: queue.Queue = queue.Queue()
        self.fila_web: queue.Queue = queue.Queue()
        self.fila_api: queue.Queue = queue.Queue()

        # Resultados finais — thread-safe
        self.resultados_finais: ResultadosThread = ResultadosThread()

        # Controle de robôs ativos
        self.lock_ativos = threading.Lock()
        self.ativos_agora: dict[str, int] = {"C3PO": 0, "R2D2": 0, "WALLE": 0}

        # Métricas e status
        self.estatisticas: dict[str, Any] = {"total_bb8": 0}
        self.status_pipeline: dict[str, bool] = {"bb8_terminou": False}

        logger.info(f"[Session {session_id[:8]}] PipelineState criado.")

    def reset(self) -> None:
        """Limpa tudo para uma nova varredura."""
        with self.fila_raw.mutex:
            self.fila_raw.queue.clear()
        with self.fila_web.mutex:
            self.fila_web.queue.clear()
        with self.fila_api.mutex:
            self.fila_api.queue.clear()

        self.resultados_finais.clear()

        with self.lock_ativos:
            self.ativos_agora = {"C3PO": 0, "R2D2": 0, "WALLE": 0}

        self.estatisticas["total_bb8"] = 0
        self.status_pipeline["bb8_terminou"] = False

        logger.info(f"[Session {self.session_id[:8]}] PipelineState resetado.")


class SessionManager:
    """
    Gerencia instâncias de PipelineState por session_id.
    Thread-safe via lock interno.
    """
    def __init__(self):
        self._sessions: dict[str, PipelineState] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> PipelineState:
        """Retorna estado existente ou cria um novo."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = PipelineState(session_id)
                logger.debug(f"Nova sessão criada: {session_id[:8]}")
            return self._sessions[session_id]

    def destroy(self, session_id: str) -> None:
        """Remove a sessão após o usuário sair da fila."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"[Session {session_id[:8]}] Estado destruído.")

    def active_count(self) -> int:
        with self._lock:
            return len(self._sessions)


# Instância global única do gerenciador de sessões
session_manager = SessionManager()

# ─── Compatibilidade retroativa (para módulos ainda não migrados) ─────────────
# Estas variáveis são uma sessão 'default' usada apenas em contextos
# onde o session_id não está disponível (ex: imports diretos legados).
_legacy_state = PipelineState("legacy-global")
fila_raw = _legacy_state.fila_raw
fila_web = _legacy_state.fila_web
fila_api = _legacy_state.fila_api
resultados_finais = _legacy_state.resultados_finais
lock_ativos = _legacy_state.lock_ativos
ativos_agora = _legacy_state.ativos_agora
estatisticas = _legacy_state.estatisticas
status_pipeline = _legacy_state.status_pipeline
