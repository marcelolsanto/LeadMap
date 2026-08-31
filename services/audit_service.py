import streamlit as st
from datetime import datetime
from services import repository


# Cores ANSI para o terminal
class Cores:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    AZUL = '\033[94m'
    ROXO = '\033[95m'
    RESET = '\033[0m'


def log_console(tipo, mensagem):
    """
    1. Imprime no Terminal.
    2. Salva no Banco de Dados com o e-mail do usuário.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Cores para o terminal
    cor = Cores.RESET
    if tipo == "ERROR":
        cor = Cores.VERMELHO
    elif tipo == "USER_ACTION":
        cor = Cores.VERDE
    elif tipo == "SYSTEM_EVENT":
        cor = Cores.AMARELO
    elif tipo == "SYNC":
        cor = Cores.ROXO
    elif tipo == "AUTH":
        cor = Cores.AZUL

    # Print Terminal
    print(f"{cor}[{timestamp}] [{tipo}] {mensagem}{Cores.RESET}")

    # Salva no Banco
    try:
        # Captura o e-mail do usuário logado
        email_usuario = "Desconhecido"
        if hasattr(st, 'session_state'):
            if 'user_info' in st.session_state and st.session_state.user_info:
                email_usuario = st.session_state.user_info.get('email', 'Anônimo')

        # Chama o repositório com a estrutura correta: Email, Ação, Detalhes
        repository.registrar_log(email_usuario, tipo, mensagem)

    except Exception as e:
        print(f"{Cores.VERMELHO}[LOG ERROR] Falha ao salvar no DB: {e}{Cores.RESET}")


def render_admin_panel():
    """Painel Admin para visualizar o banco de dados"""
    pass  # A lógica visual está no app.py conforme sua preferência
