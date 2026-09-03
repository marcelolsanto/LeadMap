"""
services/auth_service.py
Autenticação Google OAuth 2.0.

SEGURANÇA:
- Tokens OAuth NUNCA são escritos em disco — ficam apenas na session_state (memória volátil).
- Sessões persistidas por arquivo individual por usuário em data/sessions/{token}.json.
  Cada token é um UUID único gerado no momento do login, eliminando o conflito
  de arquivo compartilhado em ambientes multi-usuário.
"""
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.oauth2.credentials
import json
import os
import uuid
import requests
from datetime import datetime
from config import settings
from services import audit_service
from services import repository
from utils.logger import get_logger

logger = get_logger(__name__)

# Diretório de sessões individuais por usuário
SESSIONS_DIR = "data/sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/contacts"
]

# Duração máxima de uma sessão em segundos (24h)
SESSION_MAX_AGE_SECONDS = 86400


def get_public_ip() -> str:
    """Obtém o IP público atual para validação de segurança."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        return response.json()["ip"]
    except Exception:
        return "0.0.0.0"


def _session_file(token: str) -> str:
    """Retorna o caminho do arquivo de sessão para um token UUID."""
    safe_token = "".join(c for c in token if c.isalnum() or c == "-")
    return os.path.join(SESSIONS_DIR, f".session_{safe_token}.json")


def salvar_sessao_local(user_info: dict, session_token: str) -> None:
    """
    Salva dados basicos do usuário em arquivo por-sessao para restaurar sessao.
    SEGURANÇA: Tokens OAuth NAO sao persistidos em disco.
    Apenas: id, email, name, picture, IP de origem e timestamp.

    Args:
        user_info: dados do usuario
        session_token: token UUID unico desta sessao (armazenado na session_state)
    """
    try:
        data_to_save = {
            "id":         user_info.get("id"),
            "email":      user_info.get("email"),
            "name":       user_info.get("name"),
            "picture":    user_info.get("picture"),
            "_saved_at":  datetime.now().isoformat(),
            "_origin_ip": get_public_ip(),
            "_token":     session_token,
        }
        # Credenciais OAuth sao intencionalmente OMITIDAS do arquivo
        with open(_session_file(session_token), "w") as f:
            json.dump(data_to_save, f)
        logger.debug(f"Sessao salva para {user_info.get('email')} [{session_token[:8]}]")
    except Exception as e:
        logger.error(f"Falha ao salvar sessao local: {e}", exc_info=True)


def carregar_sessao_local(session_token: str | None = None) -> dict | None:
    """
    Tenta carregar a sessao salva pelo token especifico desta aba/navegador.
    Verifica IP e idade da sessao como medidas de seguranca.

    Args:
        session_token: token UUID armazenado em st.session_state

    NOTA: Credentials OAuth nao estao no arquivo — usuario precisara
    re-autorizar o Google para operacoes que exijam credentials.
    """
    if not session_token:
        return None

    path = _session_file(session_token)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Valida expiracao (maximo SESSION_MAX_AGE_SECONDS)
        saved_at_str = data.get("_saved_at")
        if saved_at_str:
            try:
                saved_at = datetime.fromisoformat(saved_at_str)
                age = (datetime.now() - saved_at).total_seconds()
                if age > SESSION_MAX_AGE_SECONDS:
                    logger.info(f"Sessao expirada por tempo ({age:.0f}s).")
                    limpar_sessao_local(session_token)
                    return None
            except Exception:
                pass

        # Valida IP
        ip_salvo = data.get("_origin_ip")
        ip_atual = get_public_ip()
        if ip_salvo and ip_salvo != ip_atual:
            audit_service.log_console(
                "SEC_ALERT",
                f"Troca de IP detectada ({ip_salvo} -> {ip_atual}). Solicitando novo login."
            )
            limpar_sessao_local(session_token)
            return None

        return data
    except Exception as e:
        logger.warning(f"Erro ao carregar sessao local [{session_token[:8] if session_token else '?'}]: {e}")
        return None


def limpar_sessao_local(session_token: str | None = None) -> None:
    """
    Remove o arquivo de sessao especifico e o estado OAuth.

    Args:
        session_token: token da sessao a remover. Se None, remove apenas .oauth_state.
    """
    if session_token:
        path = _session_file(session_token)
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.debug(f"Sessao removida: {session_token[:8]}")
            except Exception as e:
                logger.warning(f"Erro ao remover sessao {session_token[:8]}: {e}")

    oauth_state = ".oauth_state"
    if os.path.exists(oauth_state):
        try:
            os.remove(oauth_state)
        except Exception as e:
            logger.warning(f"Erro ao remover {oauth_state}: {e}")


def limpar_sessoes_antigas() -> int:
    """Remove arquivos de sessao com mais de SESSION_MAX_AGE_SECONDS. Retorna contagem removida."""
    removidos = 0
    try:
        for fname in os.listdir(SESSIONS_DIR):
            if not fname.startswith(".session_"):
                continue
            fpath = os.path.join(SESSIONS_DIR, fname)
            try:
                with open(fpath) as f:
                    data = json.load(f)
                saved_at_str = data.get("_saved_at")
                if saved_at_str:
                    saved_at = datetime.fromisoformat(saved_at_str)
                    if (datetime.now() - saved_at).total_seconds() > SESSION_MAX_AGE_SECONDS:
                        os.remove(fpath)
                        removidos += 1
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Erro ao limpar sessoes antigas: {e}")
    if removidos:
        logger.info(f"{removidos} sessoes expiradas removidas.")
    return removidos


def criar_flow():
    """Cria o fluxo OAuth 2.0."""
    if hasattr(settings, "GOOGLE_CLIENT_CONFIG") and settings.GOOGLE_CLIENT_CONFIG.get("web", {}).get("client_id"):
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
    """Gera o link para o botao Entrar com Google."""
    try:
        flow = criar_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        with open(".oauth_state", "w") as f:
            json.dump({"state": state, "code_verifier": getattr(flow, "code_verifier", "")}, f)
        return authorization_url
    except Exception as e:
        logger.error(f"Falha ao gerar link de login: {e}", exc_info=True)
        return "#"


def processar_login(auth_code: str) -> dict | None:
    """
    Troca o codigo OAuth pelo token e retorna dados do usuario.
    SEGURANÇA: Tokens nao sao salvos em arquivos — ficam apenas na session_state.
    Retorna dict com chave session_token para ser armazenado na session_state.
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

        service = googleapiclient.discovery.build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        email_usuario = user_info.get("email")

        # Gera token unico para esta sessao (corrige bug de arquivo compartilhado)
        session_token = str(uuid.uuid4())

        data = {
            "id":            user_info.get("id"),
            "email":         email_usuario,
            "name":          user_info.get("name"),
            "picture":       user_info.get("picture"),
            "credentials":   creds,           # Apenas na memoria (session_state)
            "session_token": session_token,   # Identificador unico desta sessao
        }

        # Persiste apenas metadados no banco (sem tokens)
        if hasattr(repository, "salvar_usuario_db"):
            repository.salvar_usuario_db(data)

        # Persiste metadados em arquivo individual por sessao (sem tokens)
        salvar_sessao_local(data, session_token)

        # Limpeza periodica de sessoes expiradas
        limpar_sessoes_antigas()

        logger.info(f"Login bem-sucedido: {email_usuario} [{session_token[:8]}]")
        return data

    except Exception as e:
        logger.error(f"Falha critica no login: {e}", exc_info=True)
        audit_service.log_console("ERRO", f"Falha critica no login: {e}")
        return None
