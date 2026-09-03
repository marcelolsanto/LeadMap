"""
views/paywall_view.py
Página de Planos e Preços com Teste Gratuito (1 busca), Plano Mensal (R$ 30) e Anual com 45% OFF (R$ 199).
"""
import streamlit as st
from services import payment_service, repository


def render_paywall(user_email: str) -> None:
    """Renderiza a página de planos com marketing de alta conversão."""

    uso_gratis = repository.obter_uso_teste_gratis(user_email)
    tem_teste_disponivel = (uso_gratis == 0)

    url_mensal = payment_service.criar_sessao_checkout(user_email, "mensal")
    url_anual = payment_service.criar_sessao_checkout(user_email, "anual")

    st.markdown("""
    <style>
    .pricing-header {
        text-align: center;
        margin-top: 10px;
        margin-bottom: 30px;
    }
    .pricing-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 480px;
        margin-bottom: 20px;
        position: relative;
    }
    .card-highlight {
        border: 2.5px solid #2563EB !important;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.18) !important;
    }
    .badge-deal {
        position: absolute;
        top: -14px;
        right: 20px;
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: white;
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.4);
    }
    .price-tag {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        margin: 10px 0 4px 0;
    }
    .price-sub {
        color: #64748B;
        font-size: 0.85rem;
        margin-bottom: 18px;
    }
    .feature-list {
        list-style: none;
        padding: 0;
        margin: 0 0 20px 0;
        color: #334155;
        font-size: 0.9rem;
        line-height: 1.8;
    }
    .feature-list li {
        margin-bottom: 6px;
    }
    </style>

    <div class="pricing-header">
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
        st.markdown(f"""
        <div class="pricing-card">
            <div>
                <span style="background-color: #F1F5F9; color: #475569; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    EXPERIMENTE
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Teste Gratuito</h3>
                <div class="price-tag">R$ 0</div>
                <div class="price-sub">1 busca completa sem compromisso</div>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
                <ul class="feature-list">
                    <li>✅ <strong>1 Varredura completa</strong> de leads</li>
                    <li>✅ Mineração Google Maps + Web</li>
                    <li>✅ Telefones e links de WhatsApp</li>
                    <li>✅ Validação de e-mails com ping</li>
                    <li>✅ Exportação em CSV e VCard (.vcf)</li>
                    <li><span style="color:#94A3B8;">❌ Sem buscas adicionais</span></li>
                </ul>
            </div>
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
        st.markdown(f"""
        <div class="pricing-card">
            <div>
                <span style="background-color: #EFF6FF; color: #1D4ED8; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    SEM FIDELIDADE
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Mensal</h3>
                <div class="price-tag">R$ 30 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/mês</span></div>
                <div class="price-sub">Cancele quando quiser • Acesso instantâneo</div>
                <hr style="border: 0; border-top: 1px solid #f1f5f9; margin-bottom: 14px;"/>
                <ul class="feature-list">
                    <li>✅ Buscas e leads <strong>ILIMITADOS</strong> por 30 dias</li>
                    <li>✅ Todas as fontes (Maps, Sites, Redes)</li>
                    <li>✅ Enriquecimento fiscal com CNPJ e Razão Social</li>
                    <li>✅ Ping de servidor em todos os e-mails</li>
                    <li>✅ Sincronizador Google Contacts</li>
                    <li>💳 Pagamento via <strong>Cartão ou PIX</strong></li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.link_button("💳 Assinar Mensal (R$ 30/mês)", url=url_mensal, use_container_width=True)

    # --- CARD 3: ANUAL (DESTAQUE) ---
    with col3:
        st.markdown(f"""
        <div class="pricing-card card-highlight">
            <div class="badge-deal">🏆 ECONOMIZE 45%</div>
            <div>
                <span style="background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
                    MAIS POPULAR
                </span>
                <h3 style="margin: 10px 0 0 0; color: #1E293B; font-size: 1.3rem;">Plano Anual</h3>
                <div style="font-size: 0.95rem; color: #94A3B8; text-decoration: line-through; margin-top: 4px;">De R$ 360,00</div>
                <div class="price-tag" style="color: #1D4ED8;">R$ 199 <span style="font-size: 1rem; color: #64748B; font-weight: 400;">/ano</span></div>
                <div class="price-sub" style="color: #059669; font-weight: 600;">Equivalente a apenas R$ 16,58/mês!</div>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 14px;"/>
                <ul class="feature-list">
                    <li>⭐ <strong>TUDO DO PLANO MENSAL</strong> incluído</li>
                    <li>⭐ <strong>Acesso ILIMITADO por 12 meses</strong></li>
                    <li>⭐ <strong>Economia real de R$ 161,00</strong> no ano</li>
                    <li>⭐ Atualizações de novos robôs inclusas</li>
                    <li>⭐ Suporte VIP prioritário via WhatsApp</li>
                    <li>💳 Pagamento parcelado no <strong>Cartão ou PIX</strong></li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.link_button("🔥 Garantir 45% OFF (R$ 199/ano)", url=url_anual, type="primary", use_container_width=True)

    st.markdown("""
    <div style="text-align: center; margin-top: 30px; color: #64748B; font-size: 0.85rem;">
        🔒 Pagamento 100% seguro com criptografia de ponta a ponta via Stripe. Acesso liberado instantaneamente.
    </div>
    """, unsafe_allow_html=True)
