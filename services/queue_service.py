import streamlit as st
import threading


# Garante uma única instância da fila para toda a aplicação (Singleton)
@st.cache_resource
def get_manager():
    return FilaManager()


class FilaManager:
    def __init__(self):
        self.fila = []  # Lista de espera [id1, id2, id3]
        self.usuario_atual = None  # Quem está usando o recurso agora
        self.lock = threading.Lock()  # Segurança para não corromper a lista

    # --- [INSERÇÃO] MÉTODO DE CONTAGEM ---
    def tamanho_fila(self):
        """Retorna quantos usuários estão esperando (excluindo quem está rodando)"""
        return len(self.fila)

    def entrar(self, session_id):
        """Adiciona o usuário na fila."""
        with self.lock:
            # Só adiciona se não estiver na fila E não for o usuário atual
            if session_id not in self.fila and self.usuario_atual != session_id:
                self.fila.append(session_id)

    def sair(self, session_id):
        """Remove o usuário da fila e libera o recurso."""
        with self.lock:
            if session_id in self.fila:
                self.fila.remove(session_id)

            # Se quem saiu era quem estava usando, libera a vaga
            if self.usuario_atual == session_id:
                self.usuario_atual = None

    def verificar_vez(self, session_id):
        """
        Retorna:
        0 -> É A SUA VEZ (Pode rodar)
        >0 -> Sua posição na fila (1, 2, 3...)
        -1 -> Não está na fila
        """
        with self.lock:
            # Se ninguém está usando
            if self.usuario_atual is None:
                # E tem gente na fila
                if len(self.fila) > 0:
                    # E eu sou o primeiro
                    if self.fila[0] == session_id:
                        self.usuario_atual = session_id  # Ocupo a vaga
                        self.fila.pop(0)  # Saio da espera
                        return 0

            # Se eu já sou o dono da vaga (ex: atualização de página)
            if self.usuario_atual == session_id:
                return 0

            # Se estou na fila, calculo minha posição
            if session_id in self.fila:
                return self.fila.index(session_id) + 1

            # Não estou na fila e não é minha vez
            return -1
