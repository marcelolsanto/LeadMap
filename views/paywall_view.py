"""
views/paywall_view.py
Página de Planos e Preços:
1. Consulta Avulsa (Pay-per-search: cada consulta um pagamento) via link oficial BTG Pactual.
2. Plano Mensal (R$ 30) via link oficial BTG Pactual.
3. Plano Anual (R$ 199 - 45% OFF) via link oficial BTG Pactual.
4. Desbloqueio Imediato com Envio de Comprovante (Upload, Código de Transação ou WhatsApp).
Suporte a pagamentos por Cartão de Crédito, Pix e Boleto Bancário via BTG Pay e QR Code PIX direto.
"""
import os
import time
import urllib.parse
import streamlit as st
from services import payment_service, repository, btg_service, audit_service
from config import settings


def _clean_html(html_str: str) -> str:
    """Remove indentação linha a linha para evitar blocos <pre><code> do Markdown."""
    return "\n".join(line.lstrip() for line in html_str.splitlines())


def render_paywall(user_email: str) -> None:
    """Renderiza a página de planos sem amostra grátis com links oficiais do BTG Pactual e área de liberação/comprovante."""

    creditos_disponiveis = repository.obter_creditos_consulta(user_email)

    link_avulso = getattr(settings, "LINK_PAGAMENTO_AVULSO", "https://links.btgpactual.com/xb6gXBfTZ0IMOMa")
    link_mensal = getattr(settings, "LINK_PAGAMENTO_MENSAL", "https://pag.ae/827QRApG9")

    link_anual = getattr(settings, "LINK_PAGAMENTO_ANUAL", "https://pag.ae/827QSc4HM")





    # Barra superior com identificação e opção de trocar de conta / sair
    header_bar = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; padding: 10px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px;">
        <span style="font-weight:bold; color:#2563eb; font-size:1.2rem;">LeadMap Pro</span>
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="font-size:0.85rem; color:#64748b;">👤 Conectado como: <strong>{user_email}</strong></span>
            <a href="?logout=true" target="_self" style="font-size:0.8rem; color:#dc2626; font-weight:600; text-decoration:none; border:1px solid #fca5a5; padding:4px 10px; border-radius:6px; background:#fff1f2;">Trocar de Conta / Sair</a>
        </div>
    </div>
    """
    st.markdown(_clean_html(header_bar), unsafe_allow_html=True)

    title_html = """
    <div style="text-align: center; margin-top: 10px; margin-bottom: 20px;">
        <h2 style="font-size: 2rem; color: #1E293B; margin-bottom: 6px; font-weight: 800;">
            ⚡ Escolha seu Acesso ao LeadMap Pro
        </h2>
        <p style="color: #64748B; font-size: 1.05rem; max-width: 680px; margin: 0 auto;">
            Escale sua prospecção B2B com mineração profunda de contatos, WhatsApp direto, e-mails com ping no servidor e inteligência fiscal.
        </p>
    </div>
    """
    st.markdown(_clean_html(title_html), unsafe_allow_html=True)


    st.info(f"👤 Conectado como: **{user_email}**. Os créditos e assinaturas adquiridos serão vinculados diretamente a esta conta.")

    if creditos_disponiveis == 0:
        st.warning("⚠️ Você não possui consultas ativas no momento. Escolha o pagamento por consulta ou um plano com consultas ilimitadas abaixo para iniciar sua pesquisa:")

    col1, col2, col3 = st.columns(3)

    # --- CARD 1: CONSULTA AVULSA (PAGAMENTO POR CONSULTA) ---
    with col1:
        st.markdown("""
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08); border: 1.5px solid #E2E8F0; min-height: 480px; margin-bottom: 15px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span style="background-color: #EFF6FF; color: #2563EB; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    PAGAMENTO POR CONSULTA
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Consulta Avulsa</h3>
                <div style="font-size: 2rem; font-weight: 800; color: #0F172A; margin: 8px 0 2px 0;">1 Pagamento <span style="font-size: 0.95rem; color: #64748B; font-weight: 400;">/consulta</span></div>
                <div style="color: #64748B; font-size: 0.85rem; margin-bottom: 16px;">Cada consulta um pagamento • 1 varredura completa</div>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
                <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.88rem; line-height: 1.8;">
                    <li>✅ <strong>1 Varredura Completa</strong> de leads</li>
                    <li>✅ Mineração Google Maps + Web</li>
                    <li>✅ Telefones e links diretos de WhatsApp</li>
                    <li>✅ Validação de e-mails com ping MX</li>
                    <li>✅ Exportação completa em CSV e VCard</li>
                    <li>💳 Pague com <strong>Cartão de Crédito ou Pix</strong></li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.link_button("💳 Pagar Consulta (Cartão / Pix)", url=link_avulso, type="primary", use_container_width=True)

        if st.button("✅ Já paguei! Liberar 1 Consulta", key="confirm_avulso", use_container_width=True):
            repository.adicionar_creditos_consulta(user_email, 1)
            audit_service.log_console("PAYMENT", f"1 Crédito de consulta liberado para {user_email}")
            st.toast("🎉 Pagamento registrado! 1 consulta liberada.", icon="✅")
            st.session_state.navegacao = "inicio"
            st.rerun()

        with st.popover("⚡ Pagar Consulta no Pix Direto", use_container_width=True):
            st.markdown("### ⚡ Pagamento de Consulta via PIX")
            st.caption("Recebimento direto na conta **BTG Pactual**")
            pix_c = btg_service.gerar_pix_copia_cola(5.00, txid="CONSULTA")
            qr_url_c = btg_service.gerar_qr_code_url(pix_c)
            st.image(qr_url_c, width=200)
            st.text_area("📋 Código Pix Copia e Cola:", value=pix_c, height=70, key="pix_area_c")
            st.caption("Chave Pix direta (CNPJ): `62.977.131/0001-80`")
            st.info("Abra o app de qualquer banco, faça o Pix para a chave CNPJ e confirme abaixo para liberar sua varredura:")

            if st.button("✅ Já fiz o Pix da Consulta! Liberar", key="confirm_pix_c", type="primary", use_container_width=True):
                repository.adicionar_creditos_consulta(user_email, 1)
                repository.salvar_comprovante_pagamento(user_email, "avulso", "pix_direto", "liberado_usuario")
                audit_service.log_console("PAYMENT", f"1 Crédito liberado via Pix Direto para {user_email}")
                st.toast("🎉 1 Consulta liberada com sucesso!", icon="✅")
                st.session_state.navegacao = "inicio"
                st.rerun()


    # --- CARD 2: MENSAL ---
    with col2:
        st.markdown("""
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08); border: 1.5px solid #E2E8F0; min-height: 480px; margin-bottom: 15px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
                <span style="background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    CONSULTAS ILIMITADAS
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Mensal</h3>
                <div style="font-size: 2.2rem; font-weight: 800; color: #0F172A; margin: 8px 0 2px 0;">R$ 30 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/mês</span></div>
                <div style="color: #64748B; font-size: 0.85rem; margin-bottom: 16px;">Sem limite de consultas • Cancele quando quiser</div>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
                <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.88rem; line-height: 1.8;">
                    <li>⭐ <strong>Consultas e Leads ILIMITADOS</strong> por 30 dias</li>
                    <li>⭐ <strong>Não precisa pagar por cada consulta!</strong></li>
                    <li>⭐ Todas as fontes (Maps, Sites, Redes)</li>
                    <li>⭐ Enriquecimento fiscal com CNPJ</li>
                    <li>⭐ Sincronizador Google Contacts</li>
                    <li>💳 Pague com <strong>Cartão de Crédito ou Pix</strong></li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.link_button("💳 Pagar Mensal (Cartão / Pix)", url=link_mensal, type="primary", use_container_width=True)
        st.markdown("""
        <div style="text-align: center; margin: 6px 0 10px 0;">
            <!-- INICIO DO BOTAO PAGBANK -->
            <a href="https://pag.ae/827QRApG9/button" target="_blank" title="Pagar com PagBank">
                <img src="https://assets.pagseguro.com.br/ps-integration-assets/botoes/pagamentos/205x30-pagar.gif" alt="Pague com PagBank - é rápido, grátis e seguro!" style="max-width: 100%; border-radius: 4px;" />
            </a>
            <!-- FIM DO BOTAO PAGBANK -->
        </div>
        """, unsafe_allow_html=True)


        with st.popover("⚡ Pagar R$ 30 no Pix Direto", use_container_width=True):

            st.markdown("### ⚡ Pagamento via PIX - R$ 30,00")
            st.caption("Recebimento direto na conta **BTG Pactual**")
            pix_m = btg_service.gerar_pix_copia_cola(30.00, txid="MENSAL")
            qr_url_m = btg_service.gerar_qr_code_url(pix_m)
            st.image(qr_url_m, width=200)
            st.text_area("📋 Código Pix Copia e Cola (com valor):", value=pix_m, height=70, key="pix_area_m")
            st.caption("Ou use a Chave Pix direta (CNPJ): `62.977.131/0001-80`")
            st.info("Abra o app de qualquer banco, escolha 'Pix Copia e Cola' e confirme o pagamento de **R$ 30,00** para **BTG Pactual**.")

            if st.button("✅ Já fiz o Pix Mensal! Liberar Acesso", key="confirm_pix_m", type="primary", use_container_width=True):
                repository.salvar_assinatura(
                    email=user_email,
                    status="active",
                    customer_id="btg_pactual_pix",
                    subscription_id="pix_mensal_30",
                    valido_ate="vitalicio"
                )
                audit_service.log_console("PAYMENT", f"Assinatura Mensal R$ 30 ativada via PIX BTG para {user_email}")
                st.toast("🎉 Pagamento registrado! Acesso liberado.", icon="✅")
                st.session_state.navegacao = "inicio"
                st.rerun()

    # --- CARD 3: ANUAL (DESTAQUE) ---
    with col3:
        st.markdown("""
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(37, 99, 235, 0.18); border: 2.5px solid #2563EB; min-height: 480px; margin-bottom: 15px; position: relative; display: flex; flex-direction: column; justify-content: space-between;">
            <div style="position: absolute; top: -14px; right: 20px; background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; padding: 4px 14px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px;">
                🏆 ECONOMIZE 45%
            </div>
            <div>
                <span style="background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    MAIS VANTAJOSO
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Anual VIP</h3>
                <div style="font-size: 0.95rem; color: #94A3B8; text-decoration: line-through; margin-top: 4px;">De R$ 360,00</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #1D4ED8; margin: 4px 0;">R$ 199 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/ano</span></div>
                <div style="color: #059669; font-size: 0.85rem; font-weight: 600; margin-bottom: 16px;">Apenas R$ 16,58/mês! (Economia de R$ 161)</div>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 14px;"/>
                <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.88rem; line-height: 1.8;">
                    <li>⭐ <strong>TUDO DO PLANO MENSAL</strong> incluído</li>
                    <li>⭐ <strong>Acesso e Buscas ILIMITADOS por 12 meses</strong></li>
                    <li>⭐ <strong>Economia real de R$ 161,00</strong> no ano</li>
                    <li>⭐ Nunca mais pague por consulta avulsa</li>
                    <li>⭐ Suporte VIP prioritário via WhatsApp</li>
                    <li>💳 Pague com <strong>Cartão de Crédito ou Pix</strong></li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.link_button("💳 Pagar Anual (Cartão / Pix - 45% OFF)", url=link_anual, type="primary", use_container_width=True)
        st.markdown("""
        <div style="text-align: center; margin: 6px 0 10px 0;">
            <!-- INICIO DO BOTAO PAGBANK -->
            <a href="https://pag.ae/827QSc4HM/button" target="_blank" title="Pagar com PagBank">
                <img src="https://assets.pagseguro.com.br/ps-integration-assets/botoes/pagamentos/205x30-pagar.gif" alt="Pague com PagBank - é rápido, grátis e seguro!" style="max-width: 100%; border-radius: 4px;" />
            </a>
            <!-- FIM DO BOTAO PAGBANK -->

        </div>
        """, unsafe_allow_html=True)

        with st.popover("⚡ Pagar R$ 199 no Pix Direto", use_container_width=True):

            st.markdown("### ⚡ Pagamento via PIX - R$ 199,00 (45% OFF)")
            st.caption("Recebimento direto na conta **BTG Pactual**")
            pix_a = btg_service.gerar_pix_copia_cola(199.00, txid="ANUAL")
            qr_url_a = btg_service.gerar_qr_code_url(pix_a)
            st.image(qr_url_a, width=200)
            st.text_area("📋 Código Pix Copia e Cola (com valor):", value=pix_a, height=70, key="pix_area_a")
            st.caption("Ou use a Chave Pix direta (CNPJ): `62.977.131/0001-80`")
            st.info("Abra o app de qualquer banco, escolha 'Pix Copia e Cola' e confirme o pagamento de **R$ 199,00** para **BTG Pactual**.")

            if st.button("✅ Já fiz o Pix Anual! Liberar Acesso", key="confirm_pix_a", type="primary", use_container_width=True):
                repository.salvar_assinatura(
                    email=user_email,
                    status="active",
                    customer_id="btg_pactual_pix",
                    subscription_id="pix_anual_199",
                    valido_ate="vitalicio"
                )
                audit_service.log_console("PAYMENT", f"Assinatura Anual R$ 199 ativada via PIX BTG para {user_email}")
                st.toast("🎉 Pagamento registrado! Acesso anual VIP liberado.", icon="✅")
                st.session_state.navegacao = "inicio"
                st.rerun()

    # --- SEÇÃO DE RECUPERAÇÃO / DESBLOQUEIO DE ACESSO COM COMPROVANTE ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🚨 **Já fez o pagamento no BTG Pactual e seu acesso não abriu? Desbloqueie aqui:**", expanded=True):
        st.markdown(f"""
        Se você concluiu o pagamento no BTG Pactual para a conta **{user_email}**, escolha uma das opções abaixo para ter seu acesso liberado imediatamente:
        """)

        tab_auto, tab_upload, tab_whatsapp = st.tabs([
            "⚡ Desbloqueio Imediato",
            "📎 Enviar Comprovante de Pagamento",
            "💬 WhatsApp de Suporte"
        ])

        with tab_auto:
            st.markdown("Confirme qual pagamento você acabou de realizar:")
            recup_tipo = st.selectbox("Modalidade paga no BTG:", [
                "Consulta Avulsa (1 Varredura)",
                "Plano Mensal (R$ 30,00)",
                "Plano Anual VIP (R$ 199,00)"
            ], key="sel_recup_tipo")

            tx_id_input = st.text_input("Código de Autenticação / ID da Transação do comprovante (opcional):", placeholder="Ex: E30306... ou ID da transação BTG", key="input_tx_recup")

            if st.button("🔓 Desbloquear Meu Acesso Imediatamente", type="primary", use_container_width=True, key="btn_desbloqueio_auto"):
                if "Avulsa" in recup_tipo:
                    repository.adicionar_creditos_consulta(user_email, 1)
                    repository.salvar_comprovante_pagamento(user_email, "avulso", tx_id_input, "desbloqueio_auto")
                    audit_service.log_console("PAYMENT", f"Desbloqueio de 1 consulta para {user_email}")
                    st.success("🎉 Pagamento confirmado! 1 Consulta liberada.")
                elif "Mensal" in recup_tipo:
                    repository.salvar_assinatura(user_email, "active", "btg_pactual", "mensal_30", "vitalicio")
                    repository.salvar_comprovante_pagamento(user_email, "mensal", tx_id_input, "desbloqueio_auto")
                    audit_service.log_console("PAYMENT", f"Desbloqueio do Plano Mensal para {user_email}")
                    st.success("🎉 Plano Mensal liberado com sucesso!")
                else:
                    repository.salvar_assinatura(user_email, "active", "btg_pactual", "anual_199", "vitalicio")
                    repository.salvar_comprovante_pagamento(user_email, "anual", tx_id_input, "desbloqueio_auto")
                    audit_service.log_console("PAYMENT", f"Desbloqueio do Plano Anual VIP para {user_email}")
                    st.success("🎉 Plano Anual VIP liberado com sucesso!")

                st.session_state.navegacao = "inicio"
                st.rerun()

        with tab_upload:
            st.markdown("Envie a foto ou PDF do seu comprovante do BTG Pactual:")
            uploaded_doc = st.file_uploader("Selecione o comprovante (PNG, JPG, PDF):", type=["png", "jpg", "jpeg", "pdf"], key="upload_doc_comp")
            tipo_doc = st.selectbox("Qual plano foi pago?", ["Consulta Avulsa", "Plano Mensal", "Plano Anual"], key="sel_doc_tipo")

            if uploaded_doc is not None:
                if st.button("📤 Enviar Comprovante e Liberar Acesso", type="primary", use_container_width=True, key="btn_subir_doc"):
                    nome_arquivo = f"{user_email}_{int(time.time())}_{uploaded_doc.name}"
                    caminho_salvo = os.path.join("data/comprovantes", nome_arquivo)
                    with open(caminho_salvo, "wb") as f:
                        f.write(uploaded_doc.getbuffer())

                    if "Avulsa" in tipo_doc:
                        repository.adicionar_creditos_consulta(user_email, 1)
                        repository.salvar_comprovante_pagamento(user_email, "avulso", "anexo_upload", nome_arquivo)
                    else:
                        repository.salvar_assinatura(user_email, "active", "btg_pactual", tipo_doc.lower(), "vitalicio")
                        repository.salvar_comprovante_pagamento(user_email, tipo_doc.lower(), "anexo_upload", nome_arquivo)

                    audit_service.log_console("PAYMENT", f"Comprovante recebido e salvo: {nome_arquivo}")
                    st.success("✅ Comprovante recebido e validado! Seu acesso foi liberado com sucesso.")
                    st.session_state.navegacao = "inicio"
                    st.rerun()

        with tab_whatsapp:
            st.markdown("Se preferir, fale com o suporte ou envie seu comprovante pelo WhatsApp:")
            texto_zap = urllib.parse.quote(f"Olá! Acabei de realizar o pagamento no BTG Pactual para o LeadMap Pro. Meu e-mail é: {user_email}. Segue meu comprovante:")
            st.link_button("💬 Enviar Comprovante no WhatsApp", url=f"https://wa.me/5561999999999?text={texto_zap}", use_container_width=True)

    st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: #64748B; font-size: 0.85rem;">
        🔒 Pagamento 100% seguro com criptografia e recebimento direto via BTG Pactual. Aceita Cartão de Crédito, Pix e Boleto. Acesso liberado instantaneamente.
    </div>
    """, unsafe_allow_html=True)
