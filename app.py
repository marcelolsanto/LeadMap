import sys
import asyncio
import os
import streamlit as st
import warnings
import sqlite3
import time
import pandas as pd
import uuid
import queue
import threading
from datetime import datetime

warnings.filterwarnings("ignore")

# Ajuste para Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

st.set_page_config(
    page_title="LeadMap | Automacao de Extracao de Leads",
    layout="centered",
    initial_sidebar_state="collapsed",
    page_icon="assets/favicon.ico")

# --- IMPORTS DO PROJETO ---
from config import settings
from modules.fila import GerenciadorFila
from scraper.core import GoogleMapsScraper
from services import auth_service, analytics_service, audit_service, queue_service, payment_service, btg_service
from views import login_view, search_view, results_view, paywall_view
from services import repository, backup_service, google_contacts
from utils.logger import get_logger

logger = get_logger(__name__)

# --- PIPELINE SERVICE E SESSION MANAGER ---
from services.pipeline_service import (
    session_manager,
    WorkerC3PO, WorkerR2D2, WorkerWallE
)
from services.webhook_server import iniciar_webhook_server

# Inicializa banco de dados e servidor webhook em background
repository.init_dbs()
iniciar_webhook_server(porta=8502)

# ==============================================================================
# MONITOR DE INATIVIDADE
# ==============================================================================
TIMEOUT_SEGUNDOS = 1800  # 30 minutos

def verificar_inatividade():
    if 'last_active' not in st.session_state:
        st.session_state.last_active = time.time()
        return

    tempo_parado = time.time() - st.session_state.last_active

    if tempo_parado > TIMEOUT_SEGUNDOS:
        st.session_state.clear()
        auth_service.limpar_sessao_local()
        st.warning("⚠️ Sessao expirada por inatividade. Faca login novamente.")
        time.sleep(2)
        st.rerun()
    else:
        st.session_state.last_active = time.time()


verificar_inatividade()


def configurar_seo():
    meta_tags = """
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>LeadMap | Automacao de Extracao de Leads</title>
    <meta name="description" content="O LeadMap e um Pipeline Autonomo de Geracao e Enriquecimento de Leads B2B em Tempo Real.">
    <meta name="keywords" content="prospeccao, leads, B2B, automacao, extracao de dados, scraper, vendas, SaaS">
    <meta name="author" content="Marcelo Santos, Valeria Batigalia">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://leadmapapp.com.br/">
    <meta property="og:title" content="LeadMap | A Maquina de Vendas B2B">
    <meta property="og:description" content="Escale sua prospeccao com inteligencia artificial multi-agente.">
    <meta property="og:image" content="https://leadmapapp.com.br/app/static/lista_contatos.png">
    <meta property="og:site_name" content="LeadMap">
    """
    st.markdown(meta_tags, unsafe_allow_html=True)


def carregar_assets():
    try:
        with open("assets/style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        with open("assets/script.js", "r", encoding="utf-8") as f:
            st.components.v1.html(f"<script>{f.read()}</script>", height=0, width=0)
    except Exception as e:
        logger.debug(f"Assets nao carregados: {e}")


configurar_seo()
carregar_assets()
analytics_service.inject_analytics()


def check_auth():
    # --- RETORNO DE PAGAMENTO BEM-SUCEDIDO (STRIPE CARTÃO OU PIX) ---
    if st.query_params.get("payment") == "success":
        email_pago = st.query_params.get("email") or st.session_state.get("user_info", {}).get("email")
        if email_pago:
            repository.salvar_assinatura(
                email=email_pago,
                status="active",
                customer_id="stripe_checkout",
                subscription_id="sub_checkout",
                valido_ate="vitalicio"
            )
            audit_service.log_console("PAYMENT", f"Assinatura liberada após pagamento para {email_pago}")
            st.toast("🎉 Pagamento confirmado via Cartão/PIX! Seu acesso foi liberado.", icon="✅")
        st.query_params.clear()
        st.session_state.navegacao = "inicio"
        st.rerun()

    # --- RETORNO DE AUTORIZAÇÃO DA API BTG PACTUAL (OAUTH CODE) ---
    if st.query_params.get("btg_code"):
        code_btg = st.query_params.get("btg_code")
        token_data = btg_service.trocar_codigo_por_token_btg(code_btg)
        if token_data:
            st.toast("🎉 Conexão autorizada com sucesso no BTG Pactual!", icon="🏦")
        st.query_params.clear()
        st.rerun()

    # --- 1. LOGOUT ---

    if st.query_params.get("logout"):
        email_saindo = st.session_state.user_info.get('email', 'Desconhecido')
        audit_service.log_console("AUTH", f"👋 Usuario fez Logout: {email_saindo}")

        token_atual = st.session_state.get("session_token")
        st.session_state.clear()
        auth_service.limpar_sessao_local(token_atual)
        st.query_params.clear()
        st.rerun()


    if st.session_state.logged_in:
        return

    # Bug 2 FIX: carrega sessão pelo token UUID individual, não por arquivo compartilhado
    token_salvo = st.session_state.get("session_token")
    sessao_salva = auth_service.carregar_sessao_local(token_salvo)
    if sessao_salva:
        st.session_state.logged_in = True
        st.session_state.user_info = sessao_salva
        st.session_state.session_token = sessao_salva.get("_token", token_salvo)
        logger.info(f"Retorno por sessao salva: {sessao_salva.get('email')}")
        st.rerun()

    code = st.query_params.get("code")
    if code:
        data = auth_service.processar_login(code)
        if data:
            st.session_state.logged_in = True
            st.session_state.user_info = data
            # Bug 2 FIX: armazena o token único desta sessão
            st.session_state.session_token = data.get("session_token")
            logger.info(f"Novo login autenticado: {data.get('email')}")
            st.query_params.clear()
            st.rerun()
    else:
        # --- 2. AGUARDANDO LOGIN ---
        if "visitante_logado" not in st.session_state:
            audit_service.log_console("VISITOR", "👀 Alguem acessou a pagina de Login.")
            st.session_state.visitante_logado = True

        login_view.render_login(auth_service.gerar_link_login())
        st.stop()


def check_payment(email: str) -> None:
    """
    Gate de pagamento & Planos:
    1. Admins (incluindo marcelolsantos30@gmail.com) têm acesso livre irrestrito.
    2. Assinantes com plano ativo no Stripe têm acesso liberado.
    3. Se o usuário ativou o modo teste gratuito e ainda não usou, libera a busca única.
    4. Caso contrário, exibe os 3 cards (Teste Gratuito 1 busca, Mensal R$ 30, Anual R$ 199 com 45% OFF).
    """
    if payment_service.verificar_status_assinatura(email):
        return  # Acesso irrestrito (Admin ou Assinante)

    # Se ativou modo teste gratuito nesta sessão:
    if st.session_state.get("modo_teste_gratis"):
        uso_gratis = repository.obter_uso_teste_gratis(email)
        if uso_gratis == 0:
            return  # Permite acessar a tela de busca para sua única busca grátis!
        else:
            st.session_state.modo_teste_gratis = False

    # Exibe a tela de planos com cards de marketing
    paywall_view.render_paywall(email)
    st.stop()


# --- GESTAO DE SESSAO ---
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

p_state = session_manager.get_or_create(st.session_state.session_id)
fila = queue_service.get_manager()

qtd_fila = fila.tamanho_fila()
if qtd_fila > 0:
    st.toast(f"🚦 Trafego Intenso: {qtd_fila} usuarios na fila de espera.", icon="🚦")

if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "user_info" not in st.session_state: st.session_state.user_info = {}
if "creds" not in st.session_state: st.session_state.creds = None
if "session_token" not in st.session_state: st.session_state.session_token = None
if "navegacao" not in st.session_state: st.session_state.navegacao = "inicio"
if "status_fila" not in st.session_state: st.session_state.status_fila = "fora"
if "df_leads" not in st.session_state: st.session_state.df_leads = pd.DataFrame()
if "termo" not in st.session_state: st.session_state.termo = ""
if "nicho_atual" not in st.session_state: st.session_state.nicho_atual = ""
if "qtd_leads_salvos" not in st.session_state: st.session_state.qtd_leads_salvos = 0
if "modo_teste_gratis" not in st.session_state: st.session_state.modo_teste_gratis = False

check_auth()

# Bug 1 FIX: gate de pagamento — verifica assinatura antes de renderizar qualquer tela
check_payment(st.session_state.user_info.get("email", ""))

# --- HEADER ---
user_email = st.session_state.user_info.get('email', 'Usuario')
user_pic = st.session_state.user_info.get('picture', '')

is_admin = user_email in settings.ADMIN_EMAILS
if is_admin:
    badge_plano = "<span style='background-color:#FEF3C7; color:#B45309; padding:4px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700; margin-right:8px;'>👑 ADMIN ILIMITADO</span>"
elif st.session_state.get("modo_teste_gratis"):
    badge_plano = "<span style='background-color:#E0E7FF; color:#4338CA; padding:4px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700; margin-right:8px;'>🎁 TESTE GRATUITO (1 BUSCA)</span>"
else:
    badge_plano = "<span style='background-color:#DEF7EC; color:#03543F; padding:4px 10px; border-radius:9999px; font-size:0.75rem; font-weight:700; margin-right:8px;'>⭐ ASSINANTE PRO</span>"

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; padding: 10px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px;">
<span style="font-weight:bold; color:#2563eb; font-size:1.2rem;">LeadMap</span>
<div style="display:flex; align-items:center;">
{badge_plano}
{f'<img src="{user_pic}" style="width:28px; border-radius:50%; margin-right:8px;">' if user_pic else ''}
<span style="font-size:0.8rem; color:#555; margin-right:10px">{user_email}</span>
<a href="?logout=true" target="_self" style="font-size:0.8rem; color:red; text-decoration:none;">Sair</a>
</div>
</div>
""", unsafe_allow_html=True)

# ========================================================
# TELA 1: INICIO
# ========================================================
if "robos_iniciados" not in st.session_state: st.session_state.robos_iniciados = False
if "ui_queue" not in st.session_state: st.session_state.ui_queue = queue.Queue()
if "buffers" not in st.session_state: st.session_state.buffers = {"BB8": [], "C3PO": [], "R2D2": [], "WALLE": []}

if st.session_state.navegacao == "inicio":
    col_esq, col_centro, col_dir = st.columns([1, 6, 1])
    with col_centro:
        with st.container():
            st.markdown("<h3 style='text-align:center'>O que voce busca hoje?</h3>", unsafe_allow_html=True)
            nicho = st.text_input("Nicho / Servicos", placeholder="Ex: Farmacia")
            c1, c2 = st.columns(2)
            with c1:
                bairro = st.text_input("Bairro / Cidade", key="ib", placeholder="Ex: Bras")
            with c2:
                cidade = st.text_input("Estado", key="ic", placeholder="Ex: Sao Paulo - SP")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🚀 INICIAR VARREDURA", type="primary", width='stretch'):
                st.session_state.last_active = time.time()
                user = st.session_state.user_info.get('email')
                logger.info(f"Usuario {user} clicou em INICIAR.")

                if nicho and bairro:
                    if st.session_state.get("modo_teste_gratis"):
                        repository.registrar_uso_teste_gratis(user)
                        st.toast("🎁 Você utilizou seu teste gratuito de 1 busca!", icon="🚀")

                    st.session_state.termo = f"{bairro}, {cidade}, {nicho}"
                    audit_service.log_console("USER_ACTION", f"Iniciou busca: '{nicho}' em '{bairro}'")

                    st.session_state.nicho_atual = nicho
                    st.session_state.qtd_leads_salvos = 0

                    # Reseta estado isolado desta sessao
                    p_state.reset()

                    creds = st.session_state.user_info.get('credentials')
                    if creds:
                        google_contacts.baixar_agenda_google(creds, user_email)

                    fila.entrar(st.session_state.session_id)
                    st.session_state.status_fila = "aguardando"
                    st.rerun()
                else:
                    st.warning("Preencha o Nicho e o Bairro!")

    if st.session_state.status_fila == "aguardando":
        my_id = st.session_state.session_id
        posicao = fila.verificar_vez(my_id)
        if posicao == 0:
            st.session_state.status_fila = "rodando"
            st.session_state.navegacao = "execucao"
            st.rerun()
        else:
            with st.status("⏳ Sistema em uso...", expanded=True):
                st.write(f"Sua posicao na fila: **{posicao}º**")
                time.sleep(3)
                st.rerun()

# ========================================================
# TELA 2: EXECUCAO (COM POLLING SEGURO)
# ========================================================
elif st.session_state.navegacao == "execucao":
    st.markdown(f"<h3 style='text-align:center'>⚡ Operacao Squad: {st.session_state.termo}</h3>",
                unsafe_allow_html=True)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        metric_raw = st.empty()
    with col_m2:
        metric_web = st.empty()
    with col_m3:
        metric_api = st.empty()
    with col_m4:
        metric_final = st.empty()
    st.write("---")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("### 🟠 BB-8"); log_bb8 = st.empty()
    with c2:
        st.markdown("### 🟡 C-3PO"); log_c3po = st.empty()
    with c3:
        st.markdown("### 🔵 R2-D2"); log_r2d2 = st.empty()
    with c4:
        st.markdown("### 🟢 Wall-E"); log_walle = st.empty()

    st.write("---")
    tabela_preview = st.empty()

    fila_logs_local = st.session_state.ui_queue

    def log_safe(robo, msg):
        fila_logs_local.put((robo, msg))

    def cb_bb8(msg):
        log_safe("BB8", msg)

    def cb_c3po(msg):
        log_safe("C3PO", msg)

    def cb_r2d2(msg):
        log_safe("R2D2", msg)

    def cb_walle(msg):
        log_safe("WALLE", msg)

    def run_bb8_thread(termo_para_busca, state_sessao):
        try:
            scraper = GoogleMapsScraper(
                termo_para_busca,
                callback_log=cb_bb8,
                fila_raw=state_sessao.fila_raw,
                estatisticas=state_sessao.estatisticas,
                status_pipeline=state_sessao.status_pipeline
            )
            # Executa o metodo assincrono em loop de eventos isolado
            asyncio.run(scraper.rodar())
        except Exception as e:
            msg_erro = str(e)
            if "TargetClosedError" in msg_erro:
                cb_bb8("⚠️ Navegador fechado inesperadamente.")
            else:
                cb_bb8(f"❌ Erro no BB-8: {e}")
                logger.error(f"Erro no BB-8 thread: {e}", exc_info=True)

    # --- SO INICIA OS ROBOS SE AINDA NAO FORAM INICIADOS ---
    if not st.session_state.robos_iniciados:
        try:
            p_state.reset()

            squad_c3po, squad_r2d2, squad_walle = [], [], []

            for i in range(4):
                robo = WorkerC3PO(
                    callback_log=cb_c3po,
                    id_robo=i + 1,
                    fila_raw=p_state.fila_raw,
                    fila_web=p_state.fila_web,
                    lock_ativos=p_state.lock_ativos,
                    ativos_agora=p_state.ativos_agora
                )
                robo.start()
                squad_c3po.append(robo)

            for i in range(18):
                robo = WorkerR2D2(
                    callback_log=cb_r2d2,
                    id_robo=i + 1,
                    fila_web=p_state.fila_web,
                    fila_api=p_state.fila_api,
                    lock_ativos=p_state.lock_ativos,
                    ativos_agora=p_state.ativos_agora
                )
                robo.start()
                squad_r2d2.append(robo)

            for i in range(2):
                robo = WorkerWallE(
                    callback_log=cb_walle,
                    id_robo=i + 1,
                    fila_api=p_state.fila_api,
                    resultados_finais=p_state.resultados_finais,
                    lock_ativos=p_state.lock_ativos,
                    ativos_agora=p_state.ativos_agora
                )
                robo.start()
                squad_walle.append(robo)

            st.session_state.t_bb8 = threading.Thread(
                target=run_bb8_thread,
                args=(st.session_state.termo, p_state)
            )
            st.session_state.t_bb8.start()

            st.session_state.squad_c3po = squad_c3po
            st.session_state.squad_r2d2 = squad_r2d2
            st.session_state.squad_walle = squad_walle

            st.session_state.robos_iniciados = True

        except Exception as e:
            st.error(f"Erro ao ligar os robos: {e}")
            logger.error(f"Erro ao inicializar squad de robos: {e}", exc_info=True)

    # --- INICIO DO POLLING DE TELA ---
    while True:
        st.session_state.last_active = time.time()

        metric_raw.metric(
            "🟠 Extraidos (BB-8)",
            p_state.estatisticas.get("total_bb8", 0),
            delta=f"{p_state.fila_raw.qsize()} na fila", delta_color="off"
        )
        metric_web.metric(
            "🟡 Em Leitura (C-3PO)",
            p_state.ativos_agora.get("C3PO", 0),
            delta=f"{p_state.fila_web.qsize()} na fila", delta_color="off"
        )
        metric_api.metric(
            "🔵 Em Auditoria (R2-D2)",
            p_state.ativos_agora.get("R2D2", 0),
            delta=f"{p_state.fila_api.qsize()} na fila", delta_color="off"
        )
        metric_final.metric(
            "✅ Prontos (Wall-E)",
            len(p_state.resultados_finais),
            delta="Higienizados", delta_color="normal"
        )

        while not st.session_state.ui_queue.empty():
            robo, msg = st.session_state.ui_queue.get()
            st.session_state.buffers[robo].append(msg)
            if len(st.session_state.buffers[robo]) > 6:
                st.session_state.buffers[robo].pop(0)

        log_bb8.code("\n".join(st.session_state.buffers["BB8"]), language="bash")
        log_c3po.code("\n".join(st.session_state.buffers["C3PO"]), language="json")
        log_r2d2.code("\n".join(st.session_state.buffers["R2D2"]), language="yaml")
        log_walle.code("\n".join(st.session_state.buffers["WALLE"]), language="diff")

        qtd_atual = len(p_state.resultados_finais)
        qtd_anterior = st.session_state.get('qtd_leads_salvos', 0)

        if qtd_atual > qtd_anterior:
            dados_user = st.session_state.get('user_info')
            email_user = dados_user.get('email') if dados_user else "anonimo"
            snapshot = p_state.resultados_finais.copy()
            backup_service.realizar_backup_total(email_user, snapshot)
            st.session_state['qtd_leads_salvos'] = qtd_atual

        if len(p_state.resultados_finais) > 0:
            try:
                df_preview = pd.json_normalize(p_state.resultados_finais.copy())
                tabela_preview.dataframe(df_preview.tail(3), width='stretch', hide_index=True)
            except Exception:
                pass

        # === VERIFICACAO DE CONCLUSAO ===
        if p_state.status_pipeline.get("bb8_terminou", False):
            if p_state.fila_raw.empty() and p_state.fila_web.empty() and p_state.fila_api.empty():
                if sum(p_state.ativos_agora.values()) == 0:
                    st.toast("⏳ O Wall-E formatou o ultimo lead. Preparando relatorios finais...", icon="🏁")
                    time.sleep(2.0)
                    break

        time.sleep(1)

    # --- CONCLUSAO E REDIRECIONAMENTO ---
    try:
        for robo in st.session_state.get("squad_c3po", []):
            if robo: robo.parar()
        for robo in st.session_state.get("squad_r2d2", []):
            if robo: robo.parar()
        for robo in st.session_state.get("squad_walle", []):
            if robo: robo.parar()
        if 't_bb8' in st.session_state and st.session_state.t_bb8 and st.session_state.t_bb8.is_alive():
            st.session_state.t_bb8.join()

        fila.sair(st.session_state.session_id)
        st.session_state.status_fila = "fora"
        st.session_state.robos_iniciados = False

        # Bug 3 FIX: libera a sessão do SessionManager para evitar memory leak
        session_manager.destroy(st.session_state.session_id)

        lista_final = p_state.resultados_finais.copy()

        if len(lista_final) > 0:
            try:
                st.session_state.df_leads = pd.json_normalize(lista_final)
            except Exception:
                st.session_state.df_leads = pd.DataFrame(lista_final)

            dados_user = st.session_state.get('user_info')
            email_user = dados_user.get('email') if dados_user else "anonimo"

            audit_service.log_console("SYSTEM", "Gerando backup final CSV...")
            sucesso_backup = backup_service.realizar_backup_total(email_user, lista_final)

            if sucesso_backup:
                st.toast("💾 Backup salvo com sucesso!", icon="✅")

            audit_service.log_console("SYSTEM", "Salvando leads no banco de dados...")

            qtd_salva = 0
            try:
                qtd_salva = repository.salvar_lote_leads(lista_final, st.session_state.nicho_atual)
            except Exception as e_db:
                logger.error(f"Erro ao salvar no banco: {e_db}", exc_info=True)

            st.balloons()
            st.success(
                f"🎉 Missao Cumprida! {len(lista_final)} processados ({qtd_salva} novos salvos no historico)."
            )

            audit_service.log_console(
                "SYSTEM_EVENT",
                f"Concluido. Total: {len(lista_final)} | Novos no DB: {qtd_salva}"
            )

            time.sleep(2)
            st.session_state.navegacao = "resultados"
            st.rerun()
        else:
            st.error("Nenhum lead encontrado. (O navegador foi fechado ou a busca falhou).")
            if st.button("Voltar"):
                st.session_state.navegacao = "inicio"
                st.rerun()

    except Exception as e:
        st.error(f"Erro Critico no Encerramento: {e}")
        logger.error(f"Erro Critico no Encerramento: {e}", exc_info=True)
        fila.sair(st.session_state.session_id)
        st.session_state.robos_iniciados = False
        if st.button("Abortar"):
            st.session_state.navegacao = "inicio"
            st.rerun()

# ========================================================
# TELA 3: RESULTADOS
# ========================================================
elif st.session_state.navegacao == "resultados":
    st.session_state.last_active = time.time()
    results_view.render_results(
        df=st.session_state.df_leads,
        termo_final=st.session_state.termo,
        creds=st.session_state.user_info.get('credentials'),
        user_email=user_email,
        nicho_atual=st.session_state.nicho_atual
    )
    if st.button("⬅️ Nova Busca"):
        st.session_state.navegacao = "inicio"
        st.rerun()
