# Arquivo: modules/fila.py
import streamlit as st
from threading import Lock


# Cria um bloqueio único na memória do seu PC
@st.cache_resource
def get_bloqueio_global():
    return Lock()

class GerenciadorFila:
    def __init__(self):
        self.lock = get_bloqueio_global()

    def tentar_rodar(self, callback_funcao, callback_status):
        status_msg = callback_status

        # Se já estiver rodando, avisa
        if self.lock.locked():
            status_msg("⏳ O Robô já está em uso! Aguarde ele terminar a busca anterior...")

        # Bloqueia e executa
        with self.lock:
            status_msg("🚀 Robô iniciado! A janela do Chrome vai abrir...")
            return callback_funcao()
