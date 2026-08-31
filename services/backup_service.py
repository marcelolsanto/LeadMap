import os
import pandas as pd
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)


def realizar_backup_total(email_usuario: str, todos_leads: list) -> bool:
    """
    Salva TODOS os leads capturados ate o momento, sobrescrevendo o arquivo anterior.
    Garante que o arquivo contenha sempre a versao mais atualizada e completa da pesquisa.
    """
    if not todos_leads:
        return False

    pasta_backups = "data/backups_usuarios"
    if not os.path.exists(pasta_backups):
        os.makedirs(pasta_backups)

    email_safe = email_usuario if email_usuario else "anonimo"
    nome_limpo = email_safe.replace("@", "_").replace(".", "_")
    caminho_arquivo = f"{pasta_backups}/backup_{nome_limpo}.csv"

    try:
        df = pd.json_normalize(todos_leads)
        df['ultima_sincronizacao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.to_csv(caminho_arquivo, mode='w', header=True, index=False, encoding='utf-8-sig')
        logger.info(f"[BACKUP TOTAL] {len(todos_leads)} leads salvos para {email_safe}.")
        return True
    except Exception as e:
        logger.error(f"[ERRO BACKUP] Falha ao salvar backup total: {e}", exc_info=True)
        return False
