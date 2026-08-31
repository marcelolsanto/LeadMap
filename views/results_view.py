import streamlit as st
import pandas as pd
from datetime import datetime


# A assinatura agora aceita todos os argumentos que o app.py envia
def render_results(df, termo_final=None, creds=None, user_email=None, nicho_atual=None):
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.success(f"✅ Varredura concluída! {len(df)} leads processados.")

    # Trabalha com uma cópia do dataframe recebido
    df_display = df.copy()

    # Reordenar colunas amigáveis
    colunas_ordem = ['Empresa', 'Telefone', 'Email', 'Site', 'Endereço', 'CNPJ', 'Razão Social', 'Tipo_Link']
    colunas_existentes = [c for c in colunas_ordem if c in df_display.columns]

    # Adicionar outras colunas que existam no df mas não estão na lista de ordem
    outras_colunas = [c for c in df_display.columns if c not in colunas_ordem]
    df_display = df_display[colunas_existentes + outras_colunas]

    # Tabs para Tabela e Cards
    tab1, tab2 = st.tabs(["📋 Visualização em Tabela", "🗂️ Visualização em Cards"])

    with tab1:
        st.dataframe(df_display, width='stretch', hide_index=True)

        # Botão de Download Nativo
        csv_str = df_display.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            label="⬇️ Baixar CSV Completo",
            data=csv_str,
            file_name=f"LeadMap_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary"
        )

    with tab2:
        st.markdown("### Preview dos Contatos")

        # Exibição dos resultados em cards
        for index, lead in df_display.iterrows():

            # --- LÓGICA DE EXIBIÇÃO INTELIGENTE DO LINK ---
            site_url = str(lead.get('Site', ''))
            tipo_link = lead.get('Tipo_Link', '')

            if site_url == 'nan' or site_url.strip() == '' or site_url == 'Não possui' or site_url == 'None':
                link_display = "<p>🚫 <strong>Link:</strong> Não possui</p>"
            elif tipo_link == "Instagram" or 'instagram.com' in site_url:
                link_display = f"<p>📸 <strong>Insta:</strong> <a href='{site_url}' target='_blank' style='color:#E1306C; text-decoration:none;'>Ver Perfil no Instagram</a></p>"
            elif tipo_link == "Facebook" or 'facebook.com' in site_url or 'fb.com' in site_url:
                link_display = f"<p>📘 <strong>Face:</strong> <a href='{site_url}' target='_blank' style='color:#1877F2; text-decoration:none;'>Ver Página no Facebook</a></p>"
            elif tipo_link == "LinkedIn" or 'linkedin.com' in site_url:
                link_display = f"<p>💼 <strong>LinkedIn:</strong> <a href='{site_url}' target='_blank' style='color:#0A66C2; text-decoration:none;'>Ver Perfil Profissional</a></p>"
            else:
                link_display = f"<p>🌐 <strong>Site Oficial:</strong> <a href='{site_url}' target='_blank' style='color:#10B981; text-decoration:none;'>Acessar Site</a></p>"

            with st.container():
                st.markdown(f"""
                <div style="
                    background-color: white; 
                    border-radius: 12px; 
                    padding: 20px; 
                    margin-bottom: 20px; 
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    border-left: 5px solid #1E3A8A;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
                        <h4 style="margin: 0; color: #1E293B; font-size: 1.25rem;">🏢 {lead.get('Empresa', 'Empresa Não Informada')}</h4>
                        <span style="background-color: #DEF7EC; color: #03543F; padding: 4px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;">Lead Encontrado</span>
                    </div>
                    <div style="color: #475569; font-size: 0.95rem; line-height: 1.6;">
                        <p style="margin: 5px 0;"><strong>📍 Endereço:</strong> {lead.get('Endereço', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>📞 Telefone:</strong> {lead.get('Telefone', 'N/A')}</p>
                        {link_display}
                        <p style="margin: 5px 0;"><strong>📧 Email:</strong> {lead.get('Email', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>📄 CNPJ:</strong> {lead.get('CNPJ', 'N/A')} - {lead.get('Razão Social', '')}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
