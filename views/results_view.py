"""
views/results_view.py
Visualização de Resultados do LeadMap Pro.
Cards Interativos, Responsivos, WhatsApp direto, Maps exato, E-mail validado, Redes Sociais e Sincronizador de Agenda.
"""
import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime

from services import export_service, contact_service, audit_service
from utils.logger import get_logger

logger = get_logger(__name__)


def render_results(df, termo_final=None, creds=None, user_email=None, nicho_atual=None):
    if df is None or len(df) == 0:
        st.warning("Nenhum lead encontrado para exibir.")
        return

    df_display = df.copy()

    # Reordenar colunas amigáveis
    colunas_ordem = [
        'Empresa', 'Telefone', 'Email', 'Site', 'Endereço', 'CNPJ',
        'Razão Social', 'Razao Social', 'Instagram', 'Facebook', 'LinkedIn',
        'Email_Valido', 'WhatsApp_Url', 'Google_Maps_Url', 'Tipo_Link'
    ]
    colunas_existentes = [c for c in colunas_ordem if c in df_display.columns]
    outras_colunas = [c for c in df_display.columns if c not in colunas_ordem]
    df_display = df_display[colunas_existentes + outras_colunas]

    # --- MÉTRICAS DE RESUMO ---
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("## 📊 Painel de Leads Minerados")

    total_leads = len(df_display)
    com_whats = sum(1 for _, r in df_display.iterrows() if r.get('WhatsApp_Url') or (r.get('Telefone') and str(r.get('Telefone')).startswith('+55')))
    com_email = sum(1 for _, r in df_display.iterrows() if r.get('Email') and str(r.get('Email')) not in ('None', 'nan', ''))
    com_cnpj = sum(1 for _, r in df_display.iterrows() if r.get('CNPJ') and str(r.get('CNPJ')) not in ('None', 'nan', ''))

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🏢 Total de Leads", total_leads)
    with m2:
        st.metric("💬 Com WhatsApp", com_whats)
    with m3:
        st.metric("✉️ Com E-mail", com_email)
    with m4:
        st.metric("📄 Com CNPJ / Fiscal", com_cnpj)

    st.write("")

    # --- BARRA DE AÇÕES EM LOTE ---
    c_btn1, c_btn2, c_btn3 = st.columns([1.2, 1.2, 1.2])

    with c_btn1:
        csv_str = df_display.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            label="📊 Baixar Planilha (.CSV)",
            data=csv_str,
            file_name=f"LeadMap_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c_btn2:
        vcf_bytes = export_service.gerar_vcf(df_display)
        st.download_button(
            label="📇 Baixar Agenda Completa (.VCF)",
            data=vcf_bytes,
            file_name=f"Agenda_LeadMap_{datetime.now().strftime('%Y%m%d_%H%M')}.vcf",
            mime="text/vcard",
            use_container_width=True
        )

    with c_btn3:
        if creds:
            if st.button("📲 Sincronizar Todos no Google", type="primary", use_container_width=True):
                with st.status("🔄 Sincronizando contatos com o Google Contacts...", expanded=True) as status_box:
                    try:
                        service = contact_service.get_service(creds)
                        nome_grupo = f"LeadMap - {nicho_atual or 'Prospecção'}"
                        gid = contact_service.criar_ou_recuperar_grupo(service, nome_grupo)
                        group_ids = [gid] if gid else None

                        progresso = st.progress(0)
                        sucessos = 0
                        for i, (_, row) in enumerate(df_display.iterrows()):
                            lead_dict = row.to_dict()
                            salvo = contact_service.salvar_contato(creds, lead_dict, service_existente=service, group_ids=group_ids)
                            if salvo:
                                sucessos += 1
                            progresso.progress((i + 1) / total_leads)

                        status_box.update(label=f"✅ {sucessos}/{total_leads} contatos sincronizados no Google Contacts!", state="complete")
                        st.toast(f"🎉 Sincronização concluída no grupo '{nome_grupo}'!", icon="✅")
                    except Exception as e:
                        st.error(f"Erro na sincronização: {e}")
                        logger.error(f"Erro ao sincronizar com Google Contacts: {e}", exc_info=True)
        else:
            st.button("📲 Sync Google (Faça Login com Google)", disabled=True, use_container_width=True)

    st.write("---")

    # --- ABAS: TABELA E CARDS ---
    tab_cards, tab_tabela = st.tabs(["🗂️ Visualização em Cards Interativos", "📋 Visualização em Tabela"])

    with tab_tabela:
        st.dataframe(df_display, width='stretch', hide_index=True)

    with tab_cards:
        st.markdown("""
        <style>
        .lead-card {
            background-color: #ffffff;
            border-radius: 14px;
            padding: 22px;
            margin-bottom: 22px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.07);
            border-left: 6px solid #2563EB;
            border-top: 1px solid #f1f5f9;
            border-right: 1px solid #f1f5f9;
            border-bottom: 1px solid #f1f5f9;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .lead-card:hover {
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
        }
        .btn-action-wa {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: #25D366;
            color: #ffffff !important;
            padding: 9px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.92rem;
            box-shadow: 0 2px 6px rgba(37,211,102,0.3);
            margin-right: 8px;
            margin-bottom: 8px;
        }
        .btn-action-mail {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: #2563EB;
            color: #ffffff !important;
            padding: 9px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.92rem;
            box-shadow: 0 2px 6px rgba(37,99,235,0.3);
            margin-right: 8px;
            margin-bottom: 8px;
        }
        .social-chip {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.82rem;
            text-decoration: none !important;
            font-weight: 500;
            margin-right: 6px;
            margin-bottom: 6px;
            border: 1px solid #e2e8f0;
        }
        .chip-insta { background-color: #FDF2F8; color: #DB2777 !important; border-color: #FBCFE8; }
        .chip-face { background-color: #EFF6FF; color: #1D4ED8 !important; border-color: #BFDBFE; }
        .chip-linkedin { background-color: #F0F9FF; color: #0284C7 !important; border-color: #BAE6FD; }
        .chip-site { background-color: #F0FDF4; color: #15803D !important; border-color: #BBF7D0; }
        .badge-verified {
            background-color: #DEF7EC;
            color: #03543F;
            padding: 3px 8px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-block;
            margin-left: 6px;
        }
        </style>
        """, unsafe_allow_html=True)

        for index, lead in df_display.iterrows():
            lead_dict = lead.to_dict()

            nome = str(lead_dict.get('Empresa') or 'Empresa Não Informada')
            telefone = str(lead_dict.get('Telefone') or '')
            if telefone in ('nan', 'None'): telefone = ''
            whatsapp_url = lead_dict.get('WhatsApp_Url') or ''
            if not whatsapp_url and telefone:
                digits = "".join(c for c in telefone if c.isdigit())
                if len(digits) in (10, 11, 12, 13):
                    if not digits.startswith('55'): digits = f"55{digits}"
                    whatsapp_url = f"https://wa.me/{digits}?text=Ol%C3%A1%2C+vi+sua+empresa+no+LeadMap"

            email = str(lead_dict.get('Email') or '')
            if email in ('nan', 'None'): email = ''
            email_valido = lead_dict.get('Email_Valido') or ''

            endereco = str(lead_dict.get('Endereço') or lead_dict.get('Endereco') or 'Endereço não informado')
            if endereco in ('nan', 'None', ''): endereco = 'Endereço não informado'

            maps_url = lead_dict.get('Google_Maps_Url') or ''
            if not maps_url and endereco != 'Endereço não informado':
                q = urllib.parse.quote_plus(f"{nome}, {endereco}".strip(", "))
                maps_url = f"https://www.google.com/maps/search/?api=1&query={q}"

            cnpj = str(lead_dict.get('CNPJ') or '')
            if cnpj in ('nan', 'None'): cnpj = ''
            razao = str(lead_dict.get('Razão Social') or lead_dict.get('Razao Social') or '')
            if razao in ('nan', 'None'): razao = ''

            insta = lead_dict.get('Instagram') or ''
            face = lead_dict.get('Facebook') or ''
            linkin = lead_dict.get('LinkedIn') or ''
            site = str(lead_dict.get('Site') or '')
            if site in ('nan', 'None', 'Nao possui'): site = ''

            # Botões de ação em HTML
            btn_wa_html = f"<a href='{whatsapp_url}' target='_blank' class='btn-action-wa'>💬 Conversar no WhatsApp</a>" if whatsapp_url else ""
            btn_mail_html = f"<a href='mailto:{email}' class='btn-action-mail'>✉️ Enviar E-mail</a>" if email else ""

            badge_email_html = f"<span class='badge-verified'>{email_valido}</span>" if (email and email_valido and "Servidor" in email_valido) else ""

            maps_link_html = f"<a href='{maps_url}' target='_blank' style='color:#1D4ED8; text-decoration:none; font-weight:500;'>📍 {endereco} <span style='font-size:0.8rem;'>↗ (Ver no Google Maps)</span></a>" if maps_url else f"📍 {endereco}"

            # Redes sociais chips
            social_chips_html = ""
            if insta and 'instagram.com' in insta:
                social_chips_html += f"<a href='{insta}' target='_blank' class='social-chip chip-insta'>📸 Instagram</a>"
            if face and ('facebook.com' in face or 'fb.com' in face):
                social_chips_html += f"<a href='{face}' target='_blank' class='social-chip chip-face'>📘 Facebook</a>"
            if linkin and 'linkedin.com' in linkin:
                social_chips_html += f"<a href='{linkin}' target='_blank' class='social-chip chip-linkedin'>💼 LinkedIn</a>"
            if site and site.startswith('http'):
                social_chips_html += f"<a href='{site}' target='_blank' class='social-chip chip-site'>🌐 Site Oficial</a>"

            cnpj_text = f"📄 <strong>CNPJ:</strong> {cnpj}" if cnpj else ""
            if razao and razao != nome:
                cnpj_text += f" &nbsp;•&nbsp; <em>{razao}</em>"

            with st.container():
                st.markdown(f"""
                <div class="lead-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #E2E8F0; padding-bottom:12px; margin-bottom:14px;">
                        <div>
                            <h3 style="margin:0; color:#1E293B; font-size:1.3rem; font-weight:700;">🏢 {nome}</h3>
                            <div style="color:#64748B; font-size:0.85rem; margin-top:4px;">{cnpj_text}</div>
                        </div>
                        <span style="background-color:#DEF7EC; color:#03543F; padding:4px 10px; border-radius:9999px; font-size:0.75rem; font-weight:600;">Lead Qualificado</span>
                    </div>

                    <div style="margin-bottom: 14px; font-size:0.95rem; line-height:1.6;">
                        <p style="margin:4px 0;">{maps_link_html}</p>
                        {f"<p style='margin:4px 0;'>📞 <strong>Telefone:</strong> {telefone}</p>" if telefone else ""}
                        {f"<p style='margin:4px 0;'>📧 <strong>E-mail:</strong> {email} {badge_email_html}</p>" if email else ""}
                    </div>

                    <div style="margin-bottom: 14px;">
                        {btn_wa_html}
                        {btn_mail_html}
                    </div>

                    {f"<div style='margin-top:8px;'>{social_chips_html}</div>" if social_chips_html else ""}
                </div>
                """, unsafe_allow_html=True)

                # Ações individuais Streamlit: vCard e Salvar no Google Contacts
                col_c1, col_c2, _ = st.columns([1.5, 1.8, 3.5])
                with col_c1:
                    vcf_card = export_service.gerar_vcf_individual(lead_dict)
                    slug_nome = "".join(c for c in nome if c.isalnum() or c == "_")[:20]
                    st.download_button(
                        label="📇 Baixar .VCF",
                        data=vcf_card,
                        file_name=f"{slug_nome}.vcf",
                        mime="text/vcard",
                        key=f"dl_vcf_{index}"
                    )
                with col_c2:
                    if creds:
                        if st.button("📲 Salvar na Agenda Google", key=f"btn_sync_{index}"):
                            ok = contact_service.salvar_contato(creds, lead_dict)
                            if ok:
                                st.toast(f"✅ '{nome}' adicionado à sua Agenda Google!", icon="🎉")
                            else:
                                st.error("Erro ao salvar contato no Google.")
