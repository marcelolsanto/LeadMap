import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# Chaves de API Opcionais
API_KEY_2CAPTCHA = os.getenv("API_KEY_2CAPTCHA")

admin_env = os.getenv("ADMIN_EMAILS", "")
_env_admins = [email.strip() for email in admin_env.split(",") if email.strip()] if admin_env else []
# Perfil privilegiado com acesso irrestrito garantido
ADMIN_EMAILS = list(set(["marcelolsantos30@gmail.com"] + _env_admins))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "marcelo2026")


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/contacts"
]

ARQUIVO_LOG = "auditoria_leadmap.csv"

# Links Oficiais de Pagamento (PagBank & BTG Pactual)
LINK_PAGAMENTO_AVULSO = os.getenv("LINK_PAGAMENTO_AVULSO", "https://links.btgpactual.com/xb6gXBfTZ0IMOMa")
LINK_PAGAMENTO_MENSAL = os.getenv("LINK_PAGAMENTO_MENSAL", "https://pag.ae/827QRApG9")
LINK_PAGAMENTO_ANUAL = os.getenv("LINK_PAGAMENTO_ANUAL", "https://pag.ae/827QSc4HM")





# Compatibilidade retroativa
BTG_LINK_PER_SEARCH = LINK_PAGAMENTO_AVULSO
BTG_LINK_MONTHLY = LINK_PAGAMENTO_MENSAL
BTG_LINK_YEARLY = LINK_PAGAMENTO_ANUAL

# BTG Pactual API & PIX Settings
BTG_CLIENT_ID = os.getenv("BTG_CLIENT_ID", "3293bc2c-676c-477c-8c7b-5aaf4eddecf0")
BTG_CLIENT_SECRET = os.getenv("BTG_CLIENT_SECRET", "1nkNOj3vbZKxyQxtuz_pbqtVaIbLB_xP5qh7Xxttv7sdZYgGtaKTcrWfu5nB5vOmBUydRvxmancrK9tbCHNX_Q")
BTG_PIX_CHAVE = os.getenv("BTG_PIX_CHAVE", "62977131000180")
BTG_BENEFICIARIO_NOME = os.getenv("BTG_BENEFICIARIO_NOME", "MARCELO SANTOS")
BTG_BENEFICIARIO_CIDADE = os.getenv("BTG_BENEFICIARIO_CIDADE", "BRASILIA")





# --- ANALYTICS & TRACKING (O Erro estava aqui: Faltavam estas linhas) ---

GA_TRACKING_ID = os.getenv("GA_TRACKING_ID")
META_PIXEL_ID = os.getenv("META_PIXEL_ID")

# --- CONFIGURAÇÕES GERAIS ---
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")
# --- CREDENCIAIS DO GOOGLE (Lendo do .env) ---
# Em vez de ler arquivo, montamos a configuração aqui
GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": [REDIRECT_URI],
        "javascript_origins": [os.getenv("BASE_URL", "http://localhost:8501")]
    }
}
