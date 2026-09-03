"""
views/login_view.py
Tela de Login com suporte a Google OAuth e Login direto por E-mail e Senha (especialmente para Desenvolvedor/Admin).
"""
import streamlit as st
from services import auth_service


def render_login(auth_url: str):
    st.markdown("""
    <div style="text-align: center; padding: 20px 10px; background: #ffffff; border-radius: 24px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); margin-top: 10px; margin-bottom: 20px;">
        <div style="font-size: 3.2rem; margin-bottom: 5px;">🚀</div>
        <h1 style="color: #1e293b; font-family: sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0; letter-spacing: -1px; line-height: 1.2;">
            O Google Maps é o seu<br><span style="color: #2563eb;">Novo Banco de Dados.</span>
        </h1>
        <p style="color: #64748b; font-size: 1rem; margin-top: 12px; line-height: 1.5;">
            Pare de copiar telefones manualmente.<br>Localização vira leads qualificados com 1 clique.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_google, tab_senha = st.tabs(["🚀 Entrar com Google", "🔐 Entrar com E-mail e Senha"])

    with tab_google:
        st.markdown(f"""
        <div style="text-align: center; padding: 15px 0;">
            <p style="color: #475569; font-size: 0.95rem; margin-bottom: 18px;">
                Acesse instantaneamente com sua conta Google para sincronização automática com a agenda:
            </p>
            <a href="{auth_url}" class="google-btn" target="_self" style="
                display: inline-block;
                background-color: #2563EB;
                color: #ffffff !important;
                padding: 14px 28px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 700;
                font-size: 1rem;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
            ">
                DESBLOQUEAR ACESSO COM GOOGLE 🔓
            </a>
            <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 15px;">
                🔐 Acesso Seguro via Google OAuth 2.0 • Teste Grátis Incluso
            </p>
        </div>
        """, unsafe_allow_html=True)

    with tab_senha:
        st.markdown("""
        <div style="padding: 10px 0;">
            <p style="color: #475569; font-size: 0.95rem; margin-bottom: 12px;">
                Login direto com e-mail e senha (Acesso Administrador / Desenvolvedor):
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_login_direto"):
            email_input = st.text_input("E-mail", placeholder="marcelolsantos30@gmail.com", key="input_login_email")
            senha_input = st.text_input("Senha", type="password", placeholder="Sua senha de acesso", key="input_login_senha")
            btn_entrar = st.form_submit_button("🔑 Entrar no LeadMap Pro", type="primary", use_container_width=True)

            if btn_entrar:
                if not email_input or not senha_input:
                    st.error("Preencha o e-mail e a senha.")
                else:
                    user_data = auth_service.autenticar_email_senha(email_input, senha_input)
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.user_info = user_data
                        st.session_state.session_token = user_data.get("session_token")
                        st.toast("🎉 Bem-vindo de volta, Administrador!", icon="👑")
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos.")

    # Rodapé institucional
    st.markdown("""
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #f1f5f9; font-size: 0.9rem; color: #64748b; text-align: center;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
            <span style="font-size: 1.5rem;">👨‍💻</span>
            <div style="text-align: left;">
                <strong style="color: #1e293b; display: block;">Desenvolvido por: Marcelo Santos</strong>
                <span style="font-size: 0.75rem;">Desenvolvedor de Sistemas, Especialista em Automação & Dados</span>
            </div>
        </div>
        <div style="margin-top: 25px; margin-bottom: 15px; font-size: 0.85rem; color: #666;">
            <a href="https://leadmapapp.com.br/privacy" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Política de Privacidade</a> 
            &nbsp;|&nbsp; 
            <a href="https://leadmapapp.com.br/terms" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Termos de Serviço</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.stop()
