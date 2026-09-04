"""
views/results_view.py
Visualização de Resultados do LeadMap Pro.
Cards Interativos, Responsivos, WhatsApp direto, Maps exato, E-mail validado, Redes Sociais e Sincronizador de Agenda.
"""
import streamlit as st
import pandas as pd
import urllib.parse
import re
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
            if endereco in ('nan', 'None', ''):
                endereco = 'Endereço não informado'
            elif endereco != 'Endereço não informado':
                endereco = re.sub(r'[\ue000-\uf8ff]', '', endereco)
                endereco = re.sub(r'\b\d+[\.,]\d+\b\s*(\(\d+\))?', '', endereco)
                endereco = re.sub(r'Fecha(\s+(às|as))?\s+\d{1,2}:\d{2}', '', endereco, flags=re.IGNORECASE)
                endereco = re.sub(r'Aberto(\s+agora)?', '', endereco, flags=re.IGNORECASE)
                endereco = re.sub(r'Rotas(\s*↗)?', '', endereco, flags=re.IGNORECASE)
                endereco = re.sub(r'·|⋅|•', ' ', endereco)
                endereco = re.sub(r'\s+', ' ', endereco).strip(" ,.-")
                if not endereco:
                    endereco = 'Endereço não informado'

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

            # Badge de qualificação do lead
            if email and whatsapp_url:
                badge_lead_html = "<span style='background-color:#F0FDF4; color:#15803D; border:1px solid #BBF7D0; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; text-decoration:none !important; white-space:nowrap;'>✨ Contato Completo</span>"
            elif whatsapp_url:
                badge_lead_html = "<span style='background-color:#F0FDF4; color:#16A34A; border:1px solid #BBF7D0; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; text-decoration:none !important; white-space:nowrap;'>💬 WhatsApp Ativo</span>"
            else:
                badge_lead_html = "<span style='background-color:#F8FAFC; color:#475569; border:1px solid #E2E8F0; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; text-decoration:none !important; white-space:nowrap;'>🏢 Lead Qualificado</span>"

            # Badge de validação do e-mail
            badge_email_html = f"<span style='background-color:#DEF7EC; color:#03543F; border:1px solid #A7F3D0; padding:2px 8px; border-radius:9999px; font-size:0.72rem; font-weight:600; margin-left:6px; text-decoration:none !important;'>{email_valido}</span>" if (email and email_valido and "Servidor" in email_valido) else ""

            # Linha de Endereço com link elegante para Google Maps (sem sublinhado)
            if maps_url:
                maps_row = f"""<div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:8px;">
<span style="font-size:1rem; line-height:1.4;">📍</span>
<div style="flex:1;">
<a href="{maps_url}" target="_blank" title="Abrir localização no Google Maps" style="text-decoration:none !important; color:#334155; font-size:0.9rem; line-height:1.4; display:inline-flex; align-items:center; flex-wrap:wrap; gap:6px;">
<span style="text-decoration:none !important;">{endereco}</span>
<span style="color:#0284C7; font-size:0.78rem; font-weight:600; background:#E0F2FE; border:1px solid #BAE6FD; padding:1px 7px; border-radius:6px; text-decoration:none !important;">🗺️ Ver no Maps ↗</span>
</a>
</div>
</div>"""
            else:
                maps_row = f"""<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; color:#64748B; font-size:0.9rem;">
<span>📍</span> <span>{endereco}</span>
</div>"""

            # Linha de Telefone / WhatsApp direto ao clicar no número (sem sublinhado)
            if whatsapp_url:
                telefone_row = f"""<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
<span style="font-size:1rem;">📞</span>
<a href="{whatsapp_url}" target="_blank" title="Clique para enviar mensagem via WhatsApp" style="text-decoration:none !important; color:#0F172A; font-weight:600; font-size:0.92rem; display:inline-flex; align-items:center; gap:8px;">
<span style="text-decoration:none !important;">{telefone}</span>
<span style="background-color:#DCFCE7; color:#15803D; border:1px solid #86EFAC; padding:2px 8px; border-radius:6px; font-size:0.75rem; font-weight:600; text-decoration:none !important;">💬 Iniciar WhatsApp ↗</span>
</a>
</div>"""
            elif telefone:
                telefone_row = f"""<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:0.9rem; color:#334155;">
<span>📞</span> <span style="font-weight:600;">{telefone}</span>
</div>"""
            else:
                telefone_row = """<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:0.88rem; color:#94A3B8; font-style:italic;">
<span>📞</span> <span>Telefone não informado</span>
</div>"""

            # Linha de E-mail com link mailto direto (sem sublinhado)
            if email:
                email_row = f"""<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
<span style="font-size:1rem;">✉️</span>
<a href="mailto:{email}" title="Clique para redigir e-mail" style="text-decoration:none !important; color:#2563EB; font-weight:500; font-size:0.92rem; display:inline-flex; align-items:center; gap:6px;">
<span style="text-decoration:none !important;">{email}</span>
<span style="color:#64748B; font-size:0.78rem; text-decoration:none !important;">(Enviar E-mail ↗)</span>
</a>
{badge_email_html}
</div>"""
            else:
                email_row = """<div style="display:flex; align-items:center; gap:8px; margin-bottom:8px; font-size:0.88rem; color:#94A3B8; font-style:italic;">
<span>✉️</span> <span>E-mail não informado</span>
</div>"""

            # Chips de Redes Sociais e Website (estilo discreto e institucional, sem sublinhado)
            chips_list = []
            if site and site.startswith('http'):
                chips_list.append(f"<a href='{site}' target='_blank' style='text-decoration:none !important; color:#1E293B !important; background:#F8FAFC; border:1px solid #CBD5E1; padding:4px 12px; border-radius:6px; font-size:0.8rem; font-weight:500; display:inline-flex; align-items:center; gap:5px;'>🌐 Site Oficial ↗</a>")
            if insta and 'instagram.com' in insta:
                chips_list.append(f"<a href='{insta}' target='_blank' style='text-decoration:none !important; color:#9D174D !important; background:#FDF2F8; border:1px solid #FBCFE8; padding:4px 12px; border-radius:6px; font-size:0.8rem; font-weight:500; display:inline-flex; align-items:center; gap:5px;'>📸 Instagram ↗</a>")
            if linkin and 'linkedin.com' in linkin:
                chips_list.append(f"<a href='{linkin}' target='_blank' style='text-decoration:none !important; color:#0369A1 !important; background:#F0F9FF; border:1px solid #BAE6FD; padding:4px 12px; border-radius:6px; font-size:0.8rem; font-weight:500; display:inline-flex; align-items:center; gap:5px;'>💼 LinkedIn ↗</a>")
            if face and ('facebook.com' in face or 'fb.com' in face):
                chips_list.append(f"<a href='{face}' target='_blank' style='text-decoration:none !important; color:#1D4ED8 !important; background:#EFF6FF; border:1px solid #BFDBFE; padding:4px 12px; border-radius:6px; font-size:0.8rem; font-weight:500; display:inline-flex; align-items:center; gap:5px;'>📘 Facebook ↗</a>")

            social_row = f"""<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; padding-top:12px; border-top:1px solid #F1F5F9;">{''.join(chips_list)}</div>""" if chips_list else ""

            # Metadados CNPJ e Razão Social
            cnpj_text = f"📄 <strong>CNPJ:</strong> {cnpj}" if cnpj else ""
            if razao and razao != nome:
                cnpj_text += f" &nbsp;•&nbsp; <em>{razao}</em>"
            cnpj_line = f"<div style='color:#64748B; font-size:0.84rem; margin-top:4px;'>{cnpj_text}</div>" if cnpj_text else ""

            # Card institucional completo
            card_html = f"""<div style="background-color:#FFFFFF; border-radius:12px; padding:20px 24px; margin-bottom:16px; border:1px solid #E2E8F0; border-left:5px solid #2563EB; box-shadow:0 1px 4px rgba(0,0,0,0.04);">
<div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #F1F5F9; padding-bottom:12px; margin-bottom:14px; gap:12px;">
<div style="flex:1;">
<h3 style="margin:0; color:#0F172A; font-size:1.18rem; font-weight:700; line-height:1.3;">🏢 {nome}</h3>
{cnpj_line}
</div>
{badge_lead_html}
</div>
<div style="font-size:0.92rem; line-height:1.5;">
{maps_row}
{telefone_row}
{email_row}
</div>
{social_row}
</div>"""

            st.markdown(_clean_html(card_html), unsafe_allow_html=True)
