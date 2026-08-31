import streamlit as st

def render_login(auth_url):
    # HTML OTIMIZADO PARA MOBILE (V37)
    # Importante: O HTML abaixo não tem recuo (indentação) para evitar
    # que o Streamlit ache que é um bloco de código.
    html_page = f"""
<div style="text-align: center; padding: 20px 10px; background: #ffffff; border-radius: 24px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); margin-top: 10px;">
<div style="margin-bottom: 25px;">
<div style="font-size: 3.5rem; margin-bottom: 5px; animation: float 3s ease-in-out infinite;">🚀</div>
<h1 style="color: #1e293b; font-family: sans-serif; font-weight: 800; font-size: 2.2rem; margin: 0; letter-spacing: -1px; line-height: 1.2;">
O Google Maps é o seu<br><span style="color: #2563eb;">Novo Banco de Dados.</span>
</h1>
<p style="color: #64748b; font-size: 1rem; margin-top: 15px; line-height: 1.5;">
Pare de copiar telefones manualmente.<br>Localização vira lucro com 1 clique.
</p>
<h4 style="margin-top: 0; color: #1e293b; font-size: 1.05rem;">O que é o LeadMap?</h4>
<p style="font-size: 0.9rem; color: #475569; margin-bottom: 15px; line-height: 1.5;">
O LeadMap é uma ferramenta de automação B2B que ajuda as equipas de vendas a extrair, organizar e validar dados públicos (leads) para prospeção de clientes.
</p>
<h4 style="margin-top: 0; color: #1e293b; font-size: 1.05rem;">Por que precisamos do seu login do Google?</h4>
<p style="font-size: 0.9rem; color: #475569; margin-bottom: 0; line-height: 1.5;">
Utilizamos a autenticação do Google para criar a sua conta de forma segura. Caso opte por exportar os leads encontrados, necessitaremos da permissão de "Contactos do Google" unicamente para guardar os novos contactos diretamente na sua agenda.
</p>
</div>

<div class="comparison-container">
<div class="list-box">
<h3 style="color: #ef4444;">🚫 Sem LeadMap</h3>
<ul>
<li class="pain-point"><span class="icon-list">❌</span> Prospecção lenta</li>
<li class="pain-point"><span class="icon-list">❌</span> Copiar/Colar manual</li>
<li class="pain-point"><span class="icon-list">❌</span> Dados velhos</li>
<li class="pain-point"><span class="icon-list">❌</span> Agenda vazia</li>
</ul>
</div>

<div class="list-box border-divider">
<h3 style="color: #10b981;">✅ Com LeadMap</h3>
<ul>
<li class="gain-point"><span class="icon-list">⚡</span> 100+ Leads/minuto</li>
<li class="gain-point"><span class="icon-list">💎</span> Dados Qualificados</li>
<li class="gain-point"><span class="icon-list">☁️</span> Sync Agenda Google</li>
<li class="gain-point"><span class="icon-list">💰</span> Vendas Imediatas</li>
</ul>
</div>
</div>

<a href="{auth_url}" class="google-btn" target="_self">
DESBLOQUEAR ACESSO AGORA 🔓
</a>

<p style="font-size: 0.8rem; color: #94a3b8; margin-top: 15px;">
🔐 Acesso Seguro via Google • Teste Grátis
</p>

<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #f1f5f9; font-size: 0.9rem; color: #64748b;">
<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
<span style="font-size: 1.5rem;">👨‍💻</span>
<div style="text-align: left;">
<strong style="color: #1e293b; display: block;">Desenvolvido por: Marcelo Santos</strong>
<span style="font-size: 0.75rem;">Desenvolvedor de Sistemas, Especialista em Automação & Dados</span>
</div>

</div>
<div style="text-align: center; margin-top: 40px; margin-bottom: 20px; font-size: 0.85rem; color: #666;">
<a href="https://leadmapapp.com.br/privacy" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Política de Privacidade</a> 
&nbsp;|&nbsp; 
<a href="https://leadmapapp.com.br/terms" target="_blank" style="color: #2563eb; text-decoration: none; font-weight: 500;">Termos de Serviço</a>
</div>
</div>
</div>
"""
    st.markdown(html_page, unsafe_allow_html=True)
    st.stop()
