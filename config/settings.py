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

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/contacts"
]

ARQUIVO_LOG = "auditoria_leadmap.csv"

# Stripe Settings
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY")
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY")
STRIPE_CHECKOUT_URL_MONTHLY = os.getenv("STRIPE_CHECKOUT_URL_MONTHLY")
STRIPE_CHECKOUT_URL_YEARLY = os.getenv("STRIPE_CHECKOUT_URL_YEARLY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
BASE_URL = os.getenv("REDIRECT_URI", "http://localhost:8501")

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
