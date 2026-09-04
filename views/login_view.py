"""
views/login_view.py
Página Inicial de Apresentação e Login do LeadMap Pro:
- Explicação completa da utilidade do LeadMap B2B.
- Tabela comparativa (Sem LeadMap vs Com LeadMap).
- Botão oficial de Login com a Conta Google (Google OAuth 2.0).
- Formulário alternativo de Login com E-mail e Senha para Desenvolvedor/Admin.
- Rodapé institucional.
"""
import streamlit as st
from services import auth_service


def _clean_html(html_str: str) -> str:
    """Remove indentação linha a linha para evitar blocos <pre><code> do Markdown."""
    return "\n".join(line.lstrip() for line in html_str.splitlines())


def render_login(auth_url: str):
    """Renderiza a landing page completa com apresentação da ferramenta e botão de login Google."""

    landing_html = f"""
    <div style="text-align: center; padding: 24px 16px; background: #ffffff; border-radius: 24px; box-shadow: 0 5px 25px rgba(0,0,0,0.06); margin-top: 10px; margin-bottom: 20px;">
        <div style="font-size: 3.5rem; margin-bottom: 8px;">🚀</div>
        <h1 style="color: #1e293b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0; letter-spacing: -0.8px; line-height: 1.2;">
            O Google Maps é o seu<br><span style="color: #2563eb;">Novo Banco de Dados.</span>
        </h1>
        <p style="color: #64748b; font-size: 1.05rem; margin-top: 14px; line-height: 1.5; max-width: 580px; margin-left: auto; margin-right: auto;">
            Pare de copiar telefones manualmente. Localização vira leads qualificados com 1 clique.
        </p>

        <div style="margin-top: 25px; padding: 18px 20px; background: #F8FAFC; border-radius: 16px; border: 1px solid #E2E8F0; text-align: left; max-width: 620px; margin-left: auto; margin-right: auto;">
            <h4 style="margin: 0 0 8px 0; color: #1e293b; font-size: 1.05rem; font-weight: 700;">💡 O que é o LeadMap Pro?</h4>
            <p style="font-size: 0.92rem; color: #475569; margin: 0 0 16px 0; line-height: 1.6;">
                O LeadMap Pro é uma plataforma de automação e inteligência de vendas B2B que extrai, organiza e valida dados públicos de empresas direto do Google Maps, sites e redes sociais para abastecer seu funil comercial.
            </p>

            <h4 style="margin: 0 0 8px 0; color: #1e293b; font-size: 1.05rem; font-weight: 700;">🔑 Por que fazer login com sua conta Google?</h4>
            <p style="font-size: 0.92rem; color: #475569; margin: 0; line-height: 1.6;">
                Utilizamos o login oficial do Google para criar e proteger seu perfil instantaneamente. Seus créditos e pesquisas ficam salvos com total segurança e você pode sincronizar os leads capturados direto na sua agenda telefônica (Google Contacts).
            </p>
        </div>

        <div style="display: flex; gap: 16px; justify-content: center; margin-top: 25px; margin-bottom: 25px; flex-wrap: wrap;">
            <div style="background: #FFF1F2; border: 1.5px solid #FECDD3; border-radius: 16px; padding: 18px; width: 260px; text-align: left;">
                <h4 style="color: #E11D48; margin-top: 0; margin-bottom: 10px; font-size: 0.95rem; font-weight: 700;">🚫 Sem LeadMap</h4>
                <ul style="list-style: none; padding: 0; margin: 0; color: #475569; font-size: 0.88rem; line-height: 2;">
                    <li>❌ Prospecção lenta e manual</li>
                    <li>❌ Copiar e colar telefones</li>
                    <li>❌ Dados velhos e desatualizados</li>
                    <li>❌ Agenda do WhatsApp vazia</li>
                </ul>
            </div>
            <div style="background: #F0FDF4; border: 1.5px solid #BBF7D0; border-radius: 16px; padding: 18px; width: 260px; text-align: left;">
                <h4 style="color: #16A34A; margin-top: 0; margin-bottom: 10px; font-size: 0.95rem; font-weight: 700;">⚡ Com LeadMap</h4>
                <ul style="list-style: none; padding: 0; margin: 0; color: #475569; font-size: 0.88rem; line-height: 2;">
                    <li>✅ 100+ Leads por minuto</li>
                    <li>✅ Telefones e WhatsApp direto</li>
                    <li>✅ Validação MX de e-mails</li>
                    <li>✅ Exportação CSV e VCard (.vcf)</li>
                </ul>
            </div>
        </div>

        <div style="text-align: center; margin: 25px 0 10px 0;">
            <a href="{auth_url}" target="_self" style="
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                background-color: #2563EB;
                color: #ffffff !important;
                padding: 16px 36px;
                border-radius: 14px;
                text-decoration: none;
                font-weight: 700;
                font-size: 1.1rem;
                box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
            ">
                <svg width="22" height="22" viewBox="0 0 24 24"><path fill="#ffffff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#ffffff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#ffffff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#ffffff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
                ENTRAR COM A CONTA GOOGLE
            </a>
            <p style="font-size: 0.82rem; color: #94A3B8; margin-top: 14px;">
                🔐 Autenticação oficial e segura via Google OAuth 2.0
            </p>
        </div>
    </div>
    """

    st.markdown(_clean_html(landing_html), unsafe_allow_html=True)

    # Acesso opcional com E-mail e Senha para Desenvolvedor/Admin
    with st.expander("🔐 Acesso Direto com E-mail e Senha (Administrador / Desenvolvedor)"):
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
    footer_html = """
    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid #f1f5f9; font-size: 0.9rem; color: #64748b; text-align: center;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
            <span style="font-size: 1.5rem;">👨‍💻</span>
            <div style="text-align: left;">
                <strong style="color: #1e293b; display: block;">Desenvolvido por: Marcelo Santos</strong>
                <span style="font-size: 0.75rem;">Desenvolvedor de Sistemas, Especialista em Automação & Dados</span>
            </div>
        </div>
        <div style="margin-top: 20px; margin-bottom: 15px; font-size: 0.85rem; color: #666;">
            <a href="https://leadmapapp.com.br/privacy" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Política de Privacidade</a> 
            &nbsp;|&nbsp; 
            <a href="https://leadmapapp.com.br/terms" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Termos de Serviço</a>
        </div>
    </div>
    """
    st.markdown(_clean_html(footer_html), unsafe_allow_html=True)

    st.stop()
