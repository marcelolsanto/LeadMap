import os

# --- CONFIGURAÇÃO ---
ARQUIVO_SAIDA = "projeto_completo_para_ia.txt"

# Pastas para IGNORAR completamente (não entra nelas)
PASTAS_IGNORAR = {
    '.venv', 'venv', '.idea', '.git', '__pycache__',
    'perfil_chrome', 'output', '.streamlit', 'playwright-report'
}

# Arquivos para IGNORAR (não copia o conteúdo)
ARQUIVOS_IGNORAR = {
    '.env',  # Segurança: Não expor senhas
    'auditoria_leadmap.csv',  # Privacidade: Dados de clientes
    'leads.csv',  # Privacidade: Dados de clientes
    ARQUIVO_SAIDA,  # Não ler o próprio arquivo de saída
    'package-lock.json',  # Arquivos de sistema chatos
    '.DS_Store',
    'Thumbs.db'
}

# Extensões permitidas (só copia arquivos de texto/código)
EXTENSOES_PERMITIDAS = {
    '.py', '.txt', '.md', '.json', '.html', '.css', '.js', '.gitignore'
}


def exportar_projeto():
    caminho_raiz = os.getcwd()
    total_arquivos = 0

    print(f"🚀 Iniciando exportação em: {caminho_raiz}")
    print(f"📄 Arquivo final: {ARQUIVO_SAIDA}\n")

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f_saida:
        # Cabeçalho do arquivo final
        f_saida.write(f"EXPORTAÇÃO DO PROJETO LEADMAP\n")
        f_saida.write("=" * 50 + "\n\n")

        for raiz, diretorios, arquivos in os.walk(caminho_raiz):
            # 1. Filtra pastas proibidas (modifica a lista 'diretorios' in-place)
            diretorios[:] = [d for d in diretorios if d not in PASTAS_IGNORAR]

            for arquivo in arquivos:
                # 2. Verifica se o arquivo deve ser ignorado pelo nome
                if arquivo in ARQUIVOS_IGNORAR:
                    continue

                # 3. Verifica se a extensão é permitida
                _, extensao = os.path.splitext(arquivo)
                if extensao.lower() not in EXTENSOES_PERMITIDAS:
                    continue

                caminho_completo = os.path.join(raiz, arquivo)
                caminho_relativo = os.path.relpath(caminho_completo, caminho_raiz)

                try:
                    # Lê o conteúdo do arquivo original
                    with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f_origem:
                        conteudo = f_origem.read()

                    # Escreve no arquivo gigante com formatação clara
                    f_saida.write(f"\n{'=' * 60}\n")
                    f_saida.write(f"ARQUIVO: {caminho_relativo}\n")
                    f_saida.write(f"{'=' * 60}\n")
                    f_saida.write(conteudo + "\n")

                    print(f"✅ Adicionado: {caminho_relativo}")
                    total_arquivos += 1

                except Exception as e:
                    print(f"❌ Erro ao ler {caminho_relativo}: {e}")

    print(f"\n✨ Concluído! {total_arquivos} arquivos exportados para '{ARQUIVO_SAIDA}'.")


if __name__ == "__main__":
    exportar_projeto()
