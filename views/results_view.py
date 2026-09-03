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

# Nomes de interface do Google Maps que devem ser ignorados se capturados
JUNK_NAMES = [
    "classificação", "todos os filtros", "horas", "resultados",
    "aberto agora", "aberto", "fechado", "patrocinado", "mais filtros"
]


def _clean_html(html_str: str) -> str:
    """
    Remove todos os espaços iniciais de cada linha para que o parser Markdown
    do Streamlit NUNCA confunda o HTML com bloco de código indentado (<pre><code>).
    """
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())


def render_results(df, termo_final=None, creds=None, user_email=None, nicho_atual=None):
    if df is None or len(df) == 0:
        st.warning("Nenhum lead encontrado para exibir.")
        return

    df_display = df.copy()

    # Filtrar eventuais ruídos de interface do Google Maps capturados como empresa
    if 'Empresa' in df_display.columns:
        def eh_lead_valido(nome):
            if not nome or str(nome).strip() in ('', 'nan', 'None'):
                return False
            n_lower = str(nome).lower().strip()
            if n_lower in JUNK_NAMES:
                return False
            if any(n_lower.startswith(j) for j in ["classificação", "todos os filtros", "filtros"]):
                return False
            if n_lower == "resultados":
                return False
            return True

        df_display = df_display[df_display['Empresa'].apply(eh_lead_valido)]

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
                    whatsapp_url = f"https://wa.me/{digits}?text=Ol%C3%A1%2C+vi+sua+empresa+no+Google+Maps"

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

            # Botões de ação em HTML com estilos inline (garante renderização impecável)
            btn_wa_html = f"<a href='{whatsapp_url}' target='_blank' style='background-color:#25D366; color:#ffffff !important; font-weight:700; font-size:0.9rem; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(37,211,102,0.3); margin-right:8px; margin-bottom:8px;'>💬 Conversar no WhatsApp</a>" if whatsapp_url else ""
            btn_mail_html = f"<a href='mailto:{email}' style='background-color:#2563EB; color:#ffffff !important; font-weight:700; font-size:0.9rem; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(37,99,235,0.3); margin-right:8px; margin-bottom:8px;'>✉️ Enviar E-mail</a>" if email else ""
            btn_maps_html = f"<a href='{maps_url}' target='_blank' style='background-color:#0284C7; color:#ffffff !important; font-weight:700; font-size:0.9rem; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 6px rgba(2,132,199,0.3); margin-right:8px; margin-bottom:8px;'>📍 Abrir no Google Maps</a>" if maps_url else ""

            badge_email_html = f"<span style='background-color:#DEF7EC; color:#03543F; padding:3px 8px; border-radius:9999px; font-size:0.75rem; font-weight:600; margin-left:6px;'>{email_valido}</span>" if (email and email_valido and "Servidor" in email_valido) else ""

            maps_link_html = f"<a href='{maps_url}' target='_blank' style='color:#1D4ED8; text-decoration:underline; font-weight:500;'>📍 {endereco} ↗</a>" if maps_url else f"📍 {endereco}"

            # Redes sociais chips com estilos inline
            social_chips_html = ""
            if insta and 'instagram.com' in insta:
                social_chips_html += f"<a href='{insta}' target='_blank' style='background-color:#FDF2F8; color:#DB2777 !important; border:1px solid #FBCFE8; padding:5px 12px; border-radius:20px; font-size:0.82rem; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:4px; margin-right:6px; margin-bottom:6px;'>📸 Instagram</a>"
            if face and ('facebook.com' in face or 'fb.com' in face):
                social_chips_html += f"<a href='{face}' target='_blank' style='background-color:#EFF6FF; color:#1D4ED8 !important; border:1px solid #BFDBFE; padding:5px 12px; border-radius:20px; font-size:0.82rem; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:4px; margin-right:6px; margin-bottom:6px;'>📘 Facebook</a>"
            if linkin and 'linkedin.com' in linkin:
                social_chips_html += f"<a href='{linkin}' target='_blank' style='background-color:#F0F9FF; color:#0284C7 !important; border:1px solid #BAE6FD; padding:5px 12px; border-radius:20px; font-size:0.82rem; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:4px; margin-right:6px; margin-bottom:6px;'>💼 LinkedIn</a>"
            if site and site.startswith('http'):
                social_chips_html += f"<a href='{site}' target='_blank' style='background-color:#F0FDF4; color:#15803D !important; border:1px solid #BBF7D0; padding:5px 12px; border-radius:20px; font-size:0.82rem; font-weight:600; text-decoration:none; display:inline-flex; align-items:center; gap:4px; margin-right:6px; margin-bottom:6px;'>🌐 Site Oficial</a>"

            cnpj_text = f"📄 <strong>CNPJ:</strong> {cnpj}" if cnpj else ""
            if razao and razao != nome:
                cnpj_text += f" &nbsp;•&nbsp; <em>{razao}</em>"

            telefone_line = f"<p style='margin:4px 0;'>📞 <strong>Telefone:</strong> {telefone}</p>" if telefone else ""
            email_line = f"<p style='margin:4px 0;'>📧 <strong>E-mail:</strong> {email} {badge_email_html}</p>" if email else ""
            actions_row = f"<div style='margin: 12px 0;'>{btn_wa_html}{btn_mail_html}{btn_maps_html}</div>" if (btn_wa_html or btn_mail_html or btn_maps_html) else ""
            social_row = f"<div style='margin-top:6px;'>{social_chips_html}</div>" if social_chips_html else ""

            # Card sem nenhuma indentação em cada linha para evitar bloco de código markdown
            card_html = f"""<div style="background-color:#ffffff; border-radius:14px; padding:20px; margin-bottom:20px; box-shadow:0 4px 12px rgba(0,0,0,0.08); border-left:6px solid #2563EB; border-top:1px solid #f1f5f9; border-right:1px solid #f1f5f9; border-bottom:1px solid #f1f5f9;">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #E2E8F0; padding-bottom:10px; margin-bottom:12px;">
<div>
<h3 style="margin:0; color:#1E293B; font-size:1.25rem; font-weight:700;">🏢 {nome}</h3>
<div style="color:#64748B; font-size:0.85rem; margin-top:3px;">{cnpj_text}</div>
</div>
<span style="background-color:#DEF7EC; color:#03543F; padding:4px 10px; border-radius:9999px; font-size:0.75rem; font-weight:600;">Lead Qualificado</span>
</div>
<div style="margin-bottom:10px; font-size:0.92rem; line-height:1.5;">
<p style="margin:4px 0;">{maps_link_html}</p>
{telefone_line}
{email_line}
</div>
{actions_row}
{social_row}
</div>"""

            st.markdown(_clean_html(card_html), unsafe_allow_html=True)

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
