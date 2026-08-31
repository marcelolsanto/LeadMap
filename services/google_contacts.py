import os
import pandas as pd
from googleapiclient.discovery import build
from utils.logger import get_logger

logger = get_logger(__name__)


def baixar_agenda_google(creds, email_usuario: str) -> bool:
    """
    Conecta na API People do Google e baixa contatos.

    REGRA DE SEGURANCA:
    1. Salva na pasta 'data/' (sem criar subpastas).
    2. Se o arquivo do usuario ja existir, NAO faz nada (nao sobrescreve).
    """
    if not creds or not email_usuario:
        return False

    try:
        email_safe = email_usuario.replace("@", "_").replace(".", "_")
        pasta_destino = "data"
        nome_arquivo = f"{pasta_destino}/agenda_google_{email_safe}.csv"

        if os.path.exists(nome_arquivo):
            logger.info(f"[BACKUP AGENDA] O arquivo '{nome_arquivo}' ja existe. Ignorando backup.")
            return True

        logger.info(f"[BACKUP AGENDA] Arquivo novo. Iniciando download para {email_usuario}...")
        service = build('people', 'v1', credentials=creds)

        todos_contatos = []
        page_token = None

        while True:
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,phoneNumbers,emailAddresses,organizations,addresses',
                pageToken=page_token
            ).execute()

            conexoes = results.get('connections', [])
            todos_contatos.extend(conexoes)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        if not todos_contatos:
            logger.info("[BACKUP AGENDA] Agenda vazia. Nenhum arquivo criado.")
            return True

        lista_limpa = []
        for pessoa in todos_contatos:
            nomes = pessoa.get('names', [])
            tels = pessoa.get('phoneNumbers', [])
            emails = pessoa.get('emailAddresses', [])
            orgs = pessoa.get('organizations', [])
            ends = pessoa.get('addresses', [])

            item = {
                "Nome": nomes[0].get('displayName') if nomes else "Sem Nome",
                "Telefone 1": tels[0].get('value') if tels else "",
                "Telefone 2": tels[1].get('value') if len(tels) > 1 else "",
                "Email": emails[0].get('value') if emails else "",
                "Empresa": orgs[0].get('name') if orgs else "",
                "Endereco": ends[0].get('formattedValue') if ends else "",
                "ID Google": pessoa.get('resourceName')
            }
            lista_limpa.append(item)

        df = pd.DataFrame(lista_limpa)
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)

        df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig')
        logger.info(f"[BACKUP AGENDA] Sucesso! Novo arquivo criado: {nome_arquivo}")
        return True

    except Exception as e:
        logger.error(f"[ERRO BACKUP AGENDA] Falha: {e}", exc_info=True)
        return False
