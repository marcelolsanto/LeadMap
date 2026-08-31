import streamlit as st

def render_search():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 2.5rem; font-weight: 800; color: #2563eb; margin: 0;">Nova Busca</h1>
        <p style="font-size: 1rem; color: #64748b;">Defina seu alvo abaixo</p>
    </div>
    """, unsafe_allow_html=True)

    # LAYOUT CENTRALIZADO:
    # Cria 3 colunas: [Espaço Vazio] [Conteúdo Central] [Espaço Vazio]
    col_esq, col_centro, col_dir = st.columns([1, 6, 1])

    with col_centro:
        # Container para agrupar inputs visualmente
        with st.container():
            nicho = st.text_input("Nicho / Serviços", placeholder="Ex: Farmácia", help="Digite o tipo de serviço que deseja buscar")

            # Sub-colunas para Bairro e Cidade ficarem lado a lado DENTRO do centro
            c1, c2 = st.columns(2)
            with c1:
                bairro = st.text_input("Bairro / Cidade", value="", key="ib", placeholder="Ex: Brás", label_visibility="visible", help="Defina a região específica")
            with c2:
                cidade = st.text_input("Estado", value="", key="ic", placeholder="Ex: São Paulo - SP", label_visibility="visible", help="Sigla do estado ou cidade principal")

            st.markdown("<br>", unsafe_allow_html=True)  # Espaçamento

            # Botão agora obedecerá o CSS de centralização
            if st.button("🚀 INICIAR VARREDURA", type="primary", help="Clique para começar a minerar leads"):
                if nicho and bairro:
                    termo_final = f"{bairro}, {cidade}, {nicho}"
                    return termo_final, nicho
                else:
                    st.warning("Preencha o Nicho e o Bairro!")

    return None, None
