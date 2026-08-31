# Arquivo: tests/functional/test_app_expanded.py
from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
import os
import pytest

APP_PATH = "app.py"
SESSION_FILE = ".user_session"

@pytest.fixture(autouse=True)
def clean_session():
    if os.path.exists(SESSION_FILE):
        os.rename(SESSION_FILE, SESSION_FILE + ".bak")
    yield
    if os.path.exists(SESSION_FILE + ".bak"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        os.rename(SESSION_FILE + ".bak", SESSION_FILE)

# --- AUXILIAR: Busca texto em toda a página ---
def buscar_texto_na_pagina(at, trecho):
    """Varre todos os elementos de texto do Streamlit procurando o trecho."""
    elementos_texto = []
    # Coleta valores de todos os tipos de containers de texto
    for tipo in ['title', 'header', 'subheader', 'markdown', 'caption', 'text', 'info', 'success', 'warning', 'error']:
        lista_elementos = getattr(at, tipo)
        elementos_texto.extend([elem.value for elem in lista_elementos])

    conteudo_completo = " | ".join(elementos_texto)
    return trecho in conteudo_completo, conteudo_completo


# --- 1. TESTE DE LOGOUT ---
def test_funcionalidade_logout():
    user_mock = {"email": "user@test.com"}
    with patch('services.auth_service.carregar_sessao_local', return_value=user_mock):
        at = AppTest.from_file(APP_PATH)
        at.session_state.logged_in = True
        at.session_state.user_info = user_mock
        at.run(timeout=5)

        encontrado, _ = buscar_texto_na_pagina(at, "logout=true")
        assert encontrado, "Link de logout não encontrado."


# --- 2. TESTE DE FILA (AGUARDANDO) ---
def test_tela_fila_aguardando():
    user_mock = {"email": "user@test.com"}

    def side_effect_sleep(seconds):
        if seconds >= 2: raise RuntimeError("StopTest")

    with patch('services.auth_service.carregar_sessao_local', return_value=user_mock), \
            patch('services.queue_service.get_manager') as mock_queue, \
            patch('time.sleep', side_effect=side_effect_sleep):

        mock_instance = MagicMock()
        mock_instance.verificar_vez.return_value = 1
        mock_queue.return_value = mock_instance

        at = AppTest.from_file(APP_PATH)
        at.session_state.logged_in = True
        at.session_state.user_info = user_mock
        at.session_state.navegacao = "inicio"
        at.session_state.status_fila = "aguardando"

        try:
            at.run(timeout=5)
        except RuntimeError:
            pass

        # Verifica UI (Status ou Texto)
        aviso_encontrado = False
        if at.status:
            for s in at.status:
                if "Sistema em uso" in s.label: aviso_encontrado = True

        if not aviso_encontrado:
            aviso_encontrado, _ = buscar_texto_na_pagina(at, "Sua posição na fila")

        assert aviso_encontrado, "UI de fila de espera não encontrada."


import streamlit as st  # Necessário para o side_effect


# --- 3. TESTE DE TELA DE EXECUÇÃO (Dashboard) ---
def test_renderizacao_tela_execucao():
    """Valida se o Dashboard carrega com o estado correto."""

    email_teste = "admin@test.com"
    user_mock = {
        "email": email_teste,
        "name": "Admin Tester",
        "picture": "http://foto.com/img.jpg",
        "credentials": MagicMock(valid=True, token="xyz")
    }

    # [MUDANÇA CRUCIAL]
    # Lança erro na PRIMEIRA chamada de sleep.
    # Isso obriga o teste a parar logo após desenhar o painel,
    # impedindo que ele entre em loops infinitos ou timeouts.
    def stop_immediately(*args, **kwargs):
        raise RuntimeError("RenderComplete")

    # Mockamos TUDO
    with patch('services.auth_service.carregar_sessao_local', return_value=user_mock), \
            patch('config.settings.ADMIN_EMAILS', [email_teste]), \
            patch('services.queue_service.get_manager') as mock_queue, \
            patch('services.pipeline_service.WorkerC3PO'), \
            patch('services.pipeline_service.WorkerR2D2'), \
            patch('services.pipeline_service.WorkerWallE'), \
            patch('threading.Thread'), \
            patch('time.sleep', side_effect=stop_immediately):  # <--- Para na 1ª tentativa

        # Fila sempre liberada
        mock_instance = MagicMock()
        mock_instance.verificar_vez.return_value = 0
        mock_queue.return_value = mock_instance

        at = AppTest.from_file(APP_PATH)

        # Injeta estado COMPLETO
        at.session_state.logged_in = True
        at.session_state.user_info = user_mock
        at.session_state.navegacao = "execucao"
        at.session_state.status_fila = "rodando"

        # Dados vitais para o dashboard não quebrar
        at.session_state.termo = "Padaria"
        at.session_state.termo_base = "Padaria"
        at.session_state.bairro_atual = "Centro"
        at.session_state.fila_bairros = ["Bairro 2"]
        at.session_state.total_acumulado = 15
        at.session_state.resultados_finais = [{"Empresa": "Teste", "Status": "Ok"}]
        at.session_state.parar_tudo = False
        at.session_state.pausado = False
        at.session_state.progresso_geral = 0.5

        # Executa
        try:
            at.run(timeout=5)
        except RuntimeError as e:
            # Se o erro for "RenderComplete", significa SUCESSO: a tela foi desenhada e paramos.
            if str(e) != "RenderComplete":
                print(f"ERRO NÃO ESPERADO: {e}")

        # Verifica Erros do Script
        if at.exception:
            print("\n" + "!" * 40)
            print(f"O SCRIPT QUEBROU COM: {at.exception[0].value}")
            print("!" * 40 + "\n")

        # Busca conteúdo na tela
        tem_radar, _ = buscar_texto_na_pagina(at, "Radar")
        tem_c3po, _ = buscar_texto_na_pagina(at, "C-3PO")
        tem_operacao, conteudo = buscar_texto_na_pagina(at, "Operação Squad")

        # Diagnóstico
        if not (tem_radar or tem_operacao):
            print("\n" + "=" * 40)
            print(" DIAGNÓSTICO DE FALHA ")
            nav = at.session_state["navegacao"] if "navegacao" in at.session_state else "NÃO ENCONTRADO"
            print(f"Navegação Final: {nav}")
            print("-" * 20)
            print("CONTEÚDO VISÍVEL:")
            # Se ainda estiver vazio, o problema é que o app não desenha nada no início do loop
            print(conteudo[
                      :1000] if conteudo.strip() else "[TELA VAZIA - O app não desenhou nada antes do primeiro sleep]")
            print("=" * 40 + "\n")

        assert tem_radar or tem_operacao, "Dashboard não carregou. Verifique o diagnóstico acima."

# --- 4. ADMIN ---
def test_painel_admin_visibilidade():
    email = "admin@leadmap.com"
    with patch('services.auth_service.carregar_sessao_local', return_value={"email": email}), \
            patch('config.settings.ADMIN_EMAILS', [email]):
        at = AppTest.from_file(APP_PATH)
        at.session_state.logged_in = True
        at.session_state.user_info = {"email": email}
        at.run(timeout=3)
        assert any("Painel Administrativo" in exp.label for exp in at.expander)
