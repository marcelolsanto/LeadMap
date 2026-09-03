"""
views/paywall_view.py
Página de Planos e Preços com Teste Gratuito (1 busca), Plano Mensal (R$ 30) e Anual com 45% OFF (R$ 199).
Suporte a Pagamento via Cartão (Stripe) e PIX Direto na conta BTG Pactual com QR Code e Copia e Cola.
"""
import streamlit as st
import urllib.parse
from services import payment_service, repository, btg_service, audit_service
from config import settings


def render_paywall(user_email: str) -> None:
    """Renderiza a página de planos com marketing de alta conversão e checkout PIX/Cartão."""

    uso_gratis = repository.obter_uso_teste_gratis(user_email)
    tem_teste_disponivel = (uso_gratis == 0)

    url_mensal = payment_service.criar_sessao_checkout(user_email, "mensal")
    url_anual = payment_service.criar_sessao_checkout(user_email, "anual")

    st.markdown("""
    <div style="text-align: center; margin-top: 10px; margin-bottom: 30px;">
        <h2 style="font-size: 2rem; color: #1E293B; margin-bottom: 6px; font-weight: 800;">
            ⚡ Escolha seu Acesso ao LeadMap Pro
        </h2>
        <p style="color: #64748B; font-size: 1.05rem; max-width: 650px; margin: 0 auto;">
            Escale sua prospecção B2B com mineração profunda de contatos, WhatsApp direto, e-mails com ping no servidor e inteligência fiscal.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not tem_teste_disponivel:
        st.info("ℹ️ Você já utilizou seu teste gratuito de 1 busca. Para continuar minerando novos leads, selecione o Plano Mensal ou Anual com 45% de desconto abaixo:")

    col1, col2, col3 = st.columns(3)

    # --- CARD 1: TESTE GRATUITO ---
    with col1:
        st.markdown("""
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0; min-height: 460px; margin-bottom: 15px;">
            <span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                EXPERIMENTE
            </span>
            <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Teste Gratuito</h3>
            <div style="font-size: 2.2rem; font-weight: 800; color: #0F172A; margin: 10px 0 4px 0;">R$ 0</div>
            <div style="color: #64748B; font-size: 0.85rem; margin-bottom: 18px;">1 busca completa sem compromisso</div>
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
            <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.9rem; line-height: 1.8;">
                <li>✅ <strong>1 Varredura completa</strong> de leads</li>
                <li>✅ Mineração Google Maps + Web</li>
                <li>✅ Telefones e links de WhatsApp</li>
                <li>✅ Validação de e-mails com ping</li>
                <li>✅ Exportação em CSV e VCard (.vcf)</li>
                <li><span style="color:#94A3B8;">❌ Sem buscas adicionais</span></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if tem_teste_disponivel:
            if st.button("🚀 Iniciar Teste Grátis (1 Busca)", type="primary", key="btn_free_trial", use_container_width=True):
                st.session_state.modo_teste_gratis = True
                st.rerun()
        else:
            st.button("❌ Teste Já Utilizado", disabled=True, key="btn_free_disabled", use_container_width=True)

    # --- CARD 2: MENSAL ---
    with col2:
        st.markdown("""
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0; min-height: 460px; margin-bottom: 15px;">
            <span style="background-color: #EFF6FF; color: #1D4ED8; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                SEM FIDELIDADE
            </span>
            <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Mensal</h3>
            <div style="font-size: 2.2rem; font-weight: 800; color: #0F172A; margin: 10px 0 4px 0;">R$ 30 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/mês</span></div>
            <div style="color: #64748B; font-size: 0.85rem; margin-bottom: 18px;">Cancele quando quiser • Acesso instantâneo</div>
            <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
            <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.9rem; line-height: 1.8;">
                <li>✅ Buscas e leads <strong>ILIMITADOS</strong> por 30 dias</li>
                <li>✅ Todas as fontes (Maps, Sites, Redes)</li>
                <li>✅ Enriquecimento fiscal com CNPJ</li>
                <li>✅ Ping de servidor em todos os e-mails</li>
                <li>✅ Sincronizador Google Contacts</li>
                <li>⚡ Pagamento via <strong>PIX BTG ou Cartão</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        btg_link_m = getattr(settings, "BTG_LINK_MONTHLY", "")
        btn_url_m = btg_link_m if btg_link_m else url_mensal
        btn_label_m = "💳 Pagar Cartão/Boleto (BTG Pactual)" if btg_link_m else "💳 Pagar no Cartão (Stripe)"

        if btn_url_m and btn_url_m != "#":
            st.link_button(btn_label_m, url=btn_url_m, use_container_width=True)

        with st.popover("⚡ Pagar R$ 30 no PIX (BTG Pactual)", use_container_width=True):
            st.markdown("### ⚡ Pagamento via PIX - R$ 30,00")
            st.caption("Recebimento direto na conta **BTG Pactual**")
            pix_m = btg_service.gerar_pix_copia_cola(30.00, txid="MENSAL")
            qr_url_m = btg_service.gerar_qr_code_url(pix_m)
            st.image(qr_url_m, width=200)
            st.text_area("📋 Código Pix Copia e Cola (com valor):", value=pix_m, height=70, key="pix_area_m")
            st.caption("Ou use a Chave Pix direta (CNPJ): `62.977.131/0001-80`")
            st.info("Abra o app de qualquer banco, escolha 'Pix Copia e Cola' e confirme o pagamento de **R$ 30,00** para **BTG Pactual**.")
            
            if st.button("✅ Já fiz o Pix! Liberar Acesso", key="confirm_pix_m", type="primary", use_container_width=True):
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
        <div style="background-color: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(37, 99, 235, 0.18); border: 2.5px solid #2563EB; min-height: 460px; margin-bottom: 15px; position: relative;">
            <div style="position: absolute; top: -14px; right: 20px; background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; padding: 4px 14px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px;">
                🏆 ECONOMIZE 45%
            </div>
            <span style="background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                MAIS POPULAR
            </span>
            <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Anual</h3>
            <div style="font-size: 0.95rem; color: #94A3B8; text-decoration: line-through; margin-top: 4px;">De R$ 360,00</div>
            <div style="font-size: 2.2rem; font-weight: 800; color: #1D4ED8; margin: 4px 0;">R$ 199 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/ano</span></div>
            <div style="color: #059669; font-size: 0.85rem; font-weight: 600; margin-bottom: 18px;">Apenas R$ 16,58/mês! (Economia de R$ 161)</div>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 14px;"/>
            <ul style="list-style: none; padding: 0; margin: 0 0 20px 0; color: #334155; font-size: 0.9rem; line-height: 1.8;">
                <li>⭐ <strong>TUDO DO PLANO MENSAL</strong> incluído</li>
                <li>⭐ <strong>Acesso ILIMITADO por 12 meses</strong></li>
                <li>⭐ <strong>Economia real de R$ 161,00</strong> no ano</li>
                <li>⭐ Atualizações de novos robôs inclusas</li>
                <li>⭐ Suporte VIP prioritário via WhatsApp</li>
                <li>⚡ Pagamento via <strong>PIX BTG ou Cartão</strong></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        btg_link_a = getattr(settings, "BTG_LINK_YEARLY", "")
        btn_url_a = btg_link_a if btg_link_a else url_anual
        btn_label_a = "💳 Pagar Cartão/Boleto (BTG Pactual - 45% OFF)" if btg_link_a else "💳 Pagar no Cartão (Stripe)"

        if btn_url_a and btn_url_a != "#":
            st.link_button(btn_label_a, url=btn_url_a, type="primary", use_container_width=True)


        with st.popover("⚡ Pagar R$ 199 no PIX (BTG Pactual)", use_container_width=True):
            st.markdown("### ⚡ Pagamento via PIX - R$ 199,00 (45% OFF)")
            st.caption("Recebimento direto na conta **BTG Pactual**")
            pix_a = btg_service.gerar_pix_copia_cola(199.00, txid="ANUAL")
            qr_url_a = btg_service.gerar_qr_code_url(pix_a)
            st.image(qr_url_a, width=200)
            st.text_area("📋 Código Pix Copia e Cola (com valor):", value=pix_a, height=70, key="pix_area_a")
            st.caption("Ou use a Chave Pix direta (CNPJ): `62.977.131/0001-80`")
            st.info("Abra o app de qualquer banco, escolha 'Pix Copia e Cola' e confirme o pagamento de **R$ 199,00** para **BTG Pactual**.")
            
            if st.button("✅ Já fiz o Pix! Liberar Acesso", key="confirm_pix_a", type="primary", use_container_width=True):
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


    st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: #64748B; font-size: 0.85rem;">
        🔒 Pagamento 100% seguro com criptografia e recebimento direto via BTG Pactual e Stripe. Acesso liberado instantaneamente.
    </div>
    """, unsafe_allow_html=True)
