import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.oauth2.credentials
import json
import os
import requests
from datetime import datetime
from config import settings
from services import audit_service
from services import repository
from utils.logger import get_logger

logger = get_logger(__name__)

SESSION_FILE = ".user_session"

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/contacts'
]


def get_public_ip() -> str:
    """Obtém o IP público atual para validação de segurança."""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except Exception:
        return "0.0.0.0"


def salvar_sessao_local(user_info: dict) -> None:
    """
    Salva dados básicos do usuário em arquivo local para restaurar sessão.
    SEGURANÇA: Tokens OAuth NÃO são persistidos em disco.
    Apenas: id, email, name, picture, IP de origem e timestamp.
    """
    try:
        data_to_save = {
            "id":       user_info.get("id"),
            "email":    user_info.get("email"),
            "name":     user_info.get("name"),
            "picture":  user_info.get("picture"),
            "_saved_at": datetime.now().isoformat(),
            "_origin_ip": get_public_ip(),
        }
        # Credenciais OAuth são intencionalmente OMITIDAS do arquivo
        with open(SESSION_FILE, "w") as f:
            json.dump(data_to_save, f)
    except Exception as e:
        logger.error(f"Falha ao salvar sessão local: {e}", exc_info=True)


def carregar_sessao_local() -> dict | None:
    """
    Tenta carregar a sessão salva localmente.
    Verifica mudança de IP como medida de segurança.
    NOTA: Credentials OAuth não estão no arquivo — usuário precisará
    re-autorizar o Google para operações que exijam credentials.
    """
    if not os.path.exists(SESSION_FILE):
        return None

    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)

        ip_salvo = data.get('_origin_ip')
        ip_atual = get_public_ip()

        if ip_salvo and ip_salvo != ip_atual:
            audit_service.log_console(
                "SEC_ALERT",
                f"Troca de IP detectada ({ip_salvo} -> {ip_atual}). Solicitando novo login."
            )
            limpar_sessao_local()
            return None

        # Não há credentials no arquivo — é esperado e correto
        return data
    except Exception as e:
        logger.warning(f"Erro ao carregar sessão local: {e}")
        return None


def criar_flow():
    """Cria o fluxo OAuth 2.0."""
    if hasattr(settings, 'GOOGLE_CLIENT_CONFIG') and settings.GOOGLE_CLIENT_CONFIG.get('web', {}).get('client_id'):
        return google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=settings.GOOGLE_CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=settings.REDIRECT_URI
        )
    return google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=settings.REDIRECT_URI
    )


def gerar_link_login() -> str:
    """Gera o link para o botão 'Entrar com Google'."""
    try:
        flow = criar_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        with open(".oauth_state", "w") as f:
            json.dump({"state": state, "code_verifier": getattr(flow, 'code_verifier', '')}, f)
        return authorization_url
    except Exception as e:
        logger.error(f"Falha ao gerar link de login: {e}", exc_info=True)
        return "#"


def processar_login(auth_code: str) -> dict | None:
    """
    Troca o código OAuth pelo token e retorna dados do usuário.
    SEGURANÇA: Tokens não são salvos em arquivos — ficam apenas na session_state.
    """
    audit_service.log_console("AUTH", "Processando retorno do Google...")
    try:
        flow = criar_flow()

        if os.path.exists(".oauth_state"):
            with open(".oauth_state", "r") as f:
                saved = json.load(f)
                flow.state = saved.get("state")
                flow.code_verifier = saved.get("code_verifier")

        flow.fetch_token(code=auth_code)
        creds = flow.credentials

        service = googleapiclient.discovery.build('oauth2', 'v2', credentials=creds)
        user_info = service.userinfo().get().execute()
        email_usuario = user_info.get('email')

        data = {
            "id":          user_info.get("id"),
            "email":       email_usuario,
            "name":        user_info.get("name"),
            "picture":     user_info.get("picture"),
            "credentials": creds   # Apenas na memória (session_state)
        }

        # Persiste apenas metadados no banco (sem tokens)
        if hasattr(repository, 'salvar_usuario_db'):
            repository.salvar_usuario_db(data)

        # Persiste metadados básicos no arquivo local (sem tokens)
        salvar_sessao_local(data)

        logger.info(f"Login bem-sucedido: {email_usuario}")
        return data

    except Exception as e:
        logger.error(f"Falha critica no login: {e}", exc_info=True)
        audit_service.log_console("ERRO", f"Falha critica no login: {e}")
        return None


def limpar_sessao_local() -> None:
    """Remove o arquivo de sessão local para efetuar logout."""
    for f in [SESSION_FILE, ".oauth_state"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                logger.warning(f"Erro ao remover {f}: {e}")
