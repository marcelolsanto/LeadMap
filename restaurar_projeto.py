import os
import re

# Nome do arquivo gigante que contém o código
ARQUIVO_FONTE = "projeto_completo_para_ia.txt"


def restaurar():
    if not os.path.exists(ARQUIVO_FONTE):
        print(f"❌ Erro: O arquivo '{ARQUIVO_FONTE}' não foi encontrado nesta pasta.")
        return

    print(f"📂 Lendo {ARQUIVO_FONTE}...")

    with open(ARQUIVO_FONTE, "r", encoding="utf-8") as f:
        conteudo_total = f.read()

    # O padrão de separação que identificamos no seu arquivo
    # Procura por: ============================================================ (quebra de linha) ARQUIVO: nome_do_arquivo
    padrao_separador = r"={60}\nARQUIVO: (.+?)\n={60}\n"

    # Divide o conteúdo com base no separador, mantendo o nome do arquivo
    partes = re.split(padrao_separador, conteudo_total)

    # O primeiro elemento geralmente é o cabeçalho antes do primeiro arquivo, ignoramos
    arquivos_criados = 0

    # O split retorna: [texto_antes, nome_arq1, conteudo_arq1, nome_arq2, conteudo_arq2...]
    # Por isso pulamos o 0 e iteramos de 2 em 2
    for i in range(1, len(partes), 2):
        caminho_arquivo = partes[i].strip()
        conteudo_arquivo = partes[i + 1]

        # Remove linhas vazias extras no final que podem ter sido geradas pelo split
        conteudo_arquivo = conteudo_arquivo.strip() + "\n"

        # Cria os diretórios necessários (ex: modules, scraper, config)
        diretorio = os.path.dirname(caminho_arquivo)
        if diretorio and not os.path.exists(diretorio):
            os.makedirs(diretorio)
            print(f"📁 Pasta criada: {diretorio}")

        # Escreve o arquivo
        try:
            with open(caminho_arquivo, "w", encoding="utf-8") as f_out:
                f_out.write(conteudo_arquivo)
            print(f"✅ Restaurado: {caminho_arquivo}")
            arquivos_criados += 1
        except Exception as e:
            print(f"❌ Erro ao criar {caminho_arquivo}: {e}")

    print("\n" + "=" * 40)
    print(f"🚀 Restauração Concluída!")
    print(f"📄 Total de arquivos gerados: {arquivos_criados}")
    print("=" * 40)

    # Criação automática do .env (que não estava no backup)
    if not os.path.exists(".env"):
        print("\n⚠️ Criando arquivo .env de exemplo (Preencha com suas chaves!)...")
        env_content = """# CONFIGURAÇÕES DO GOOGLE
GOOGLE_CLIENT_ID="seu_client_id_aqui"
GOOGLE_CLIENT_SECRET="seu_client_secret_aqui"
REDIRECT_URI="http://localhost:8501"

# CONFIGURAÇÕES DE PAGAMENTO (STRIPE)
STRIPE_API_KEY="sk_test_..."
STRIPE_PRICE_MONTHLY="price_..."
STRIPE_PRICE_YEARLY="price_..."

# FERRAMENTAS EXTRAS
API_KEY_2CAPTCHA="sua_chave_2captcha_aqui"
GA_TRACKING_ID=""
META_PIXEL_ID=""

# ADMIN
ADMIN_EMAILS="seu_email@gmail.com"
"""
        with open(".env", "w", encoding="utf-8") as f_env:
            f_env.write(env_content)
        print("✅ Arquivo .env criado.")


if __name__ == "__main__":
    restaurar()
