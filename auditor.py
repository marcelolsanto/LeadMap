import os
import fnmatch

# Configuração: O que consideramos "Lixo" ou "Ignorável" em projetos Python/Streamlit
PADROES_IGNORE = [
    # Ambientes e Configs Locais
    '.venv', 'venv', 'env', '.idea', '.vscode', '.git',

    # Compilados Python
    '__pycache__', '*.pyc', '*.pyo', '*.pyd',

    # Logs e Temporários
    '*.log', '*.tmp', '.DS_Store', 'Thumbs.db',

    # Playwright e Streamlit caches
    '.streamlit', 'test-results', 'playwright-report'
]


def is_lixo(nome_arquivo):
    """Verifica se o arquivo/pasta bate com algum padrão de lixo"""
    for padrao in PADROES_IGNORE:
        if fnmatch.fnmatch(nome_arquivo, padrao):
            return True
    return False


def gerar_arvore(raiz, prefixo="", arquivo=None):
    itens = sorted(os.listdir(raiz))
    # Filtra para não entrar em loop infinito dentro de venvs gigantes
    itens = [i for i in itens if i != '.git']

    contagem = len(itens)

    for i, item in enumerate(itens):
        caminho_completo = os.path.join(raiz, item)
        eh_ultimo = (i == contagem - 1)

        # Desenho da árvore
        conector = "└── " if eh_ultimo else "├── "

        # Análise de Lixo
        marcador = ""
        if is_lixo(item):
            marcador = " ⚠️ [LIXO/IGNORAR]"

        # Escreve no arquivo
        linha = f"{prefixo}{conector}{item}{marcador}\n"
        arquivo.write(linha)
        print(linha.strip())  # Mostra no terminal também

        if os.path.isdir(caminho_completo):
            # Se for pasta de lixo (ex: .venv), não entra nela para não poluir o txt
            if is_lixo(item):
                arquivo.write(
                    f"{prefixo}{'    ' if eh_ultimo else '│   '}    └── ... (Conteúdo oculto: pasta de sistema)\n")
            else:
                extensao_prefixo = "    " if eh_ultimo else "│   "
                gerar_arvore(caminho_completo, prefixo + extensao_prefixo, arquivo)


if __name__ == "__main__":
    nome_saida = "estrutura_projeto.txt"
    dir_atual = os.getcwd()

    print(f"🔍 Analisando diretório: {dir_atual}\n")

    with open(nome_saida, "w", encoding="utf-8") as f:
        f.write(f"RELATÓRIO DE ESTRUTURA - LeadMap\n")
        f.write(f"Gerado em: {os.getcwd()}\n")
        f.write("=" * 50 + "\n\n")
        gerar_arvore(dir_atual, arquivo=f)
        f.write("\n" + "=" * 50 + "\n")
        f.write("LEGENDA: ⚠️ [LIXO/IGNORAR] = Sugestão para deletar ou colocar no .gitignore")

    print(f"\n✅ Relatório salvo em: {nome_saida}")
