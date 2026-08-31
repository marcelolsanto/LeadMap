import google.oauth2.credentials
from googleapiclient.discovery import build
from services import audit_service
import pandas as pd
import time


def get_service(creds):
    """Constrói e retorna o serviço da API People."""
    # print("[DEBUG] Construindo serviço do Google People API...") # Comentado para limpar log
    return build('people', 'v1', credentials=creds)


def criar_ou_recuperar_grupo(service, nome_grupo):
    """Verifica se um grupo existe. Se não, cria."""
    try:
        if not nome_grupo: return None

        # Pausa leve para leitura
        time.sleep(0.2)

        response = service.contactGroups().list(pageSize=1000).execute()
        grupos = response.get('contactGroups', [])

        for grupo in grupos:
            if grupo.get('formattedName') == nome_grupo:
                # audit_service.log_console("SYNC", f"Grupo encontrado: {nome_grupo}")
                return grupo.get('resourceName')

        audit_service.log_console("SYNC", f"Criando novo grupo: {nome_grupo}")
        novo_grupo = {"contactGroup": {"name": nome_grupo}}

        # Pausa para criação
        time.sleep(1.0)
        g = service.contactGroups().create(body=novo_grupo).execute()
        return g.get('resourceName')

    except Exception as e:
        audit_service.log_console("ERROR", f"Falha grupo '{nome_grupo}': {e}")
        return None


def tratar_valor(valor):
    """Converte NaN/None para string vazia ou None seguro para JSON."""
    if pd.isna(valor) or valor in ["nan", "NaN", "None", ""]:
        return None
    return str(valor).strip()


def salvar_contato(creds, contato, service_existente=None, group_ids=None):
    """Salva um contato no Google com marcadores e log detalhado."""
    try:
        # Rate Limit (Respeita ~55 requests/min)
        time.sleep(1.1)

        service = service_existente if service_existente else get_service(creds)

        memberships = []
        if group_ids:
            for gid in group_ids:
                if gid:
                    memberships.append({
                        "contactGroupMembership": {
                            "contactGroupResourceName": gid
                        }
                    })

        # Prepara dados (Já higienizados pelo Wall-E)
        nome_empresa = tratar_valor(contato.get("Empresa")) or "Sem Nome"
        razao_social = tratar_valor(contato.get("Razão Social")) or nome_empresa

        # Pega as colunas 'Email' e 'Telefone' que o Wall-E já limpou e priorizou
        email = tratar_valor(contato.get("Email"))
        telefone = tratar_valor(contato.get("Telefone"))
        site = tratar_valor(contato.get("Site"))

        # Monta o Log de Auditoria
        log_msg = f"{nome_empresa} -> 📧 {email or '---'} | 📞 {telefone or '---'}"
        audit_service.log_console("SYNC", log_msg)

        body = {
            "names": [{"givenName": nome_empresa}],
            "organizations": [{"name": razao_social, "title": "LeadMap Lead"}],
            "memberships": memberships,
            "emailAddresses": [],
            "phoneNumbers": [],
            "urls": []
        }

        if email:
            body["emailAddresses"].append({"value": email, "type": "work"})

        if telefone:
            body["phoneNumbers"].append({"value": telefone, "type": "work"})

        if site:
            body["urls"].append({"value": site, "type": "work"})

        service.people().createContact(body=body).execute()
        return True

    except Exception as e:
        # Retry para erro de Cota (429)
        if "429" in str(e):
            try:
                audit_service.log_console("WARN", f"Cota cheia. Pausa de 5s para: {nome_empresa}...")
                time.sleep(5)
                service.people().createContact(body=body).execute()
                audit_service.log_console("SYNC", f"Salvo após retry: {nome_empresa}")
                return True
            except Exception as e2:
                audit_service.log_console("ERROR", f"Falha definitiva {nome_empresa}: {e2}")
                pass
        else:
            audit_service.log_console("ERROR", f"Erro ao salvar {nome_empresa}: {e}")

        return False
