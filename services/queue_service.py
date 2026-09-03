import streamlit as st
import threading
import time


# Garante uma unica instancia da fila para toda a aplicacao (Singleton)
@st.cache_resource
def get_manager():
    return FilaManager()


# Timeout maximo que um slot pode ser ocupado sem atividade (30 minutos)
SLOT_TIMEOUT_SEGUNDOS = 1800


class FilaManager:
    def __init__(self):
        self.fila = []             # Lista de espera [id1, id2, id3]
        self.usuario_atual = None  # Quem esta usando o recurso agora
        self.inicio_uso = None     # Timestamp de quando o slot foi tomado
        self.lock = threading.Lock()

    def tamanho_fila(self):
        """Retorna quantos usuarios estao esperando (excluindo quem esta rodando)."""
        return len(self.fila)

    def _liberar_se_expirado(self):
        """Libera automaticamente o slot se o usuario atual expirou (sem lock externo)."""
        if self.usuario_atual and self.inicio_uso:
            tempo_ocupado = time.time() - self.inicio_uso
            if tempo_ocupado > SLOT_TIMEOUT_SEGUNDOS:
                from utils.logger import get_logger
                logger = get_logger(__name__)
                logger.warning(
                    f"Slot expirado por inatividade ({tempo_ocupado:.0f}s). "
                    f"Liberando sessao: {self.usuario_atual[:8]}..."
                )
                self.usuario_atual = None
                self.inicio_uso = None

    def entrar(self, session_id):
        """Adiciona o usuario na fila."""
        with self.lock:
            self._liberar_se_expirado()
            if session_id not in self.fila and self.usuario_atual != session_id:
                self.fila.append(session_id)

    def sair(self, session_id):
        """Remove o usuario da fila e libera o recurso."""
        with self.lock:
            if session_id in self.fila:
                self.fila.remove(session_id)
            if self.usuario_atual == session_id:
                self.usuario_atual = None
                self.inicio_uso = None

    def renovar(self, session_id):
        """Renova o timestamp de atividade do usuario atual (heartbeat)."""
        with self.lock:
            if self.usuario_atual == session_id:
                self.inicio_uso = time.time()

    def verificar_vez(self, session_id):
        """
        Retorna:
        0  -> E A SUA VEZ (Pode rodar)
        >0 -> Sua posicao na fila (1, 2, 3...)
        -1 -> Nao esta na fila
        """
        with self.lock:
            self._liberar_se_expirado()

            # Se ninguem esta usando
            if self.usuario_atual is None:
                if len(self.fila) > 0 and self.fila[0] == session_id:
                    self.usuario_atual = session_id
                    self.inicio_uso = time.time()
                    self.fila.pop(0)
                    return 0

            # Se eu ja sou o dono da vaga (ex: atualizacao de pagina)
            if self.usuario_atual == session_id:
                return 0

            # Se estou na fila, calculo minha posicao
            if session_id in self.fila:
                return self.fila.index(session_id) + 1

            return -1
