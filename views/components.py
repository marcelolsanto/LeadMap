import streamlit as st
import os

def aplicar_estilos_css():
    """Carrega o CSS global do sistema."""
    try:
        # Caminho absoluto para garantir carregamento
        caminho_css = os.path.join("assets", "style.css")
        if os.path.exists(caminho_css):
            with open(caminho_css, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Erro ao carregar estilos: {e}")


def renderizar_header_usuario(user_info: dict):
    """Renderiza a barra superior com avatar e logout."""
    email = user_info.get('email', 'Visitante')
    foto = user_info.get('picture', '')

    html_header = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; 
                padding: 10px 15px; background: white; border-radius: 12px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom:20px;">
        <span style="font-weight:bold; color:#2563eb; font-size:1.1rem;">
            📍 LeadMap Pro <span style="font-size:0.7rem; color:#999;">v2.0</span>
        </span>
        <div style="display:flex; align-items:center; gap: 10px;">
            {f'<img src="{foto}" style="width:32px; border-radius:50%; border:2px solid #e2e8f0;">' if foto else ''}
            <div style="line-height:1.2;">
                <span style="display:block; font-size:0.8rem; font-weight:600; color:#333;">{email}</span>
                <a href="?logout=true" style="font-size:0.7rem; color:#ef4444; text-decoration:none;">Sair do Sistema</a>
            </div>
        </div>
    </div>
    """
    st.markdown(html_header, unsafe_allow_html=True)


def inject_seo_meta():
    """Injeta metadados de SEO (Refatorado do original [cite: 268-270])."""
    meta_tags = """
    <meta name="description" content="Automação de Leads B2B com IA">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """
    st.markdown(meta_tags, unsafe_allow_html=True)
