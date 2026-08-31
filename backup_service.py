import os
import pandas as pd
from datetime import datetime


def realizar_backup_total(email_usuario, todos_leads):
    """
    Salva TODOS os leads capturados até o momento, sobrescrevendo o arquivo anterior.
    Garante que o arquivo contenha sempre a versão mais atualizada e completa da pesquisa.
    """
    if not todos_leads:
        return

    # Define a pasta de backups
    pasta_backups = "data/backups_usuarios"
    if not os.path.exists(pasta_backups):
        os.makedirs(pasta_backups)

    # Cria nome de arquivo seguro
    email_safe = email_usuario if email_usuario else "anonimo"
    nome_limpo = email_safe.replace("@", "_").replace(".", "_")
    caminho_arquivo = f"{pasta_backups}/backup_{nome_limpo}.csv"

    try:
        # Transforma a lista completa em Tabela
        # json_normalize lida melhor com colunas que podem variar
        df = pd.json_normalize(todos_leads)

        # Adiciona coluna de controle
        df['ultima_sincronizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # [MUDANÇA AQUI] mode='w' sobrescreve o arquivo inteiro sempre
        df.to_csv(caminho_arquivo, mode='w', header=True, index=False, encoding='utf-8-sig')

        print(f"[BACKUP TOTAL] Arquivo atualizado com {len(todos_leads)} leads para {email_safe}.")
        return True

    except Exception as e:
        print(f"[ERRO BACKUP] Falha ao salvar backup total: {e}")
        return False
