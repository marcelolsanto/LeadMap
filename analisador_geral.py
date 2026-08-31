import os
import sqlite3
import pandas as pd

# Configurações de Pastas
DIRETORIO_DADOS = "data"
DIRETORIO_SAIDA = "relatorios_completos"


def analisar_tudo():
    # 1. Cria pasta para salvar os relatórios se não existir
    if not os.path.exists(DIRETORIO_SAIDA):
        os.makedirs(DIRETORIO_SAIDA)
        print(f"📁 Pasta '{DIRETORIO_SAIDA}' criada.")

    # 2. Lista todos os arquivos .db na pasta data/
    if not os.path.exists(DIRETORIO_DADOS):
        print(f"❌ Erro: Pasta '{DIRETORIO_DADOS}' não encontrada.")
        return

    arquivos_db = [f for f in os.listdir(DIRETORIO_DADOS) if f.endswith('.db')]

    if not arquivos_db:
        print("⚠️ Nenhum banco de dados (.db) encontrado.")
        return

    print(f"🔍 Encontrados {len(arquivos_db)} bancos de dados. Iniciando extração...\n")

    # 3. Loop por cada Banco de Dados
    for db_file in arquivos_db:
        caminho_db = os.path.join(DIRETORIO_DADOS, db_file)
        nome_banco = db_file.replace('.db', '')

        print(f"💾 CONECTANDO: {db_file}")

        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()

            # Descobre quais tabelas existem neste banco
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabelas = cursor.fetchall()

            if not tabelas:
                print(f"   └── [Vazio] Nenhuma tabela encontrada.")

            for tabela_tupla in tabelas:
                nome_tabela = tabela_tupla[0]

                # Ignora tabelas internas do SQLite
                if nome_tabela.startswith('sqlite_'):
                    continue

                # Lê a tabela inteira
                df = pd.read_sql_query(f"SELECT * FROM {nome_tabela}", conn)

                # Exporta para CSV
                nome_arquivo_saida = f"{nome_banco}__{nome_tabela}.csv"
                caminho_saida = os.path.join(DIRETORIO_SAIDA, nome_arquivo_saida)

                df.to_csv(caminho_saida, index=False, encoding='utf-8-sig')

                print(f"   ├── Tabela '{nome_tabela}': {len(df)} registros exportados.")
                print(f"   └── Arquivo gerado: {caminho_saida}")

            conn.close()
            print("-" * 50)

        except Exception as e:
            print(f"❌ Erro ao ler {db_file}: {e}")

    print("\n✅ ANÁLISE CONCLUÍDA! Verifique a pasta 'relatorios_completos'.")


if __name__ == "__main__":
    analisar_tudo()
