"""
services/email_validator.py
Validador de e-mails com ping de servidor DNS/MX e verificação de entrega.
Utiliza dnspython e smtplib com cache em memória para alta performance.
"""
import re
import socket
import smtplib
from functools import lru_cache
from utils.logger import get_logger

logger = get_logger(__name__)

# Padrões e domínios descartáveis ou inválidos
BLACKLIST_TERMS = (
    "sentry", "wixpress", "noreply", "nao-responda", "no-reply",
    "usuario@", "exemplo.com", "domain.com", "email@", "teste@",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".js", ".css", ".svg",
    "hostmaster@", "postmaster@", "webmaster@", "support@wix",
    "instagram.com", "facebook.com", "fb.com", "wa.me", "whatsapp.com",
    "linktr.ee", "linkedin.com", "youtube.com", "tiktok.com"
)


def validar_sintaxe_email(email: str) -> str | None:
    """Verifica sintaxe básica do e-mail e blacklist."""
    if not email or not isinstance(email, str):
        return None
    email_limpo = email.lower().strip()
    if any(term in email_limpo for term in BLACKLIST_TERMS):
        return None
    padrao = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(padrao, email_limpo):
        return email_limpo
    return None


@lru_cache(maxsize=1024)
def obter_servidores_mx(dominio: str) -> list[str]:
    """
    Consulta registros DNS MX do domínio com cache.
    Retorna lista de hosts MX ordenados por prioridade.
    """
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
        resolver.lifetime = 4.0
        resolver.timeout = 2.5

        answers = resolver.resolve(dominio, "MX")
        mx_records = sorted(answers, key=lambda r: r.preference)
        return [str(r.exchange).rstrip(".") for r in mx_records]
    except Exception as e:
        logger.debug(f"Falha ao consultar MX para {dominio}: {e}")
        # Tenta fallback para registro A
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '1.1.1.1']
            resolver.lifetime = 3.0
            resolver.resolve(dominio, "A")
            return [dominio]
        except Exception:
            return []



def ping_servidor_smtp(mx_host: str, timeout: float = 2.5) -> bool:
    """
    Envia um ping ao servidor de correio via socket/SMTP.
    Retorna True se o servidor aceitou a conexão inicial.
    """
    if not mx_host:
        return False
    try:
        server = smtplib.SMTP(timeout=timeout)
        code, _ = server.connect(mx_host, 25)
        if code in (220, 250):
            server.helo("leadmapapp.com.br")
            server.quit()
            return True
        server.close()
    except (socket.timeout, socket.error, smtplib.SMTPException, OSError) as e:
        logger.debug(f"Ping SMTP {mx_host}:25 falhou ou filtrado ({e}).")
    return False


def validar_email_completo(email: str, verificar_ping: bool = True) -> tuple[str | None, bool, str]:
    """
    Validação em camadas:
    1. Sintaxe e Blacklist
    2. DNS MX Records (Servidor de correio existente)
    3. Ping SMTP (Handshake de confirmação de servidor ativo)

    Retorna:
        (email_normalizado, is_valido, status_legivel)
    """
    email_limpo = validar_sintaxe_email(email)
    if not email_limpo:
        return None, False, "Sintaxe inválida ou blacklist"

    partes = email_limpo.split("@")
    if len(partes) != 2:
        return None, False, "Formato incorreto"

    dominio = partes[1]
    servidores_mx = obter_servidores_mx(dominio)

    if not servidores_mx:
        return None, False, f"Domínio @{dominio} não possui servidor de e-mail ativo"

    # Se possui servidores MX, o domínio é válido e recebe e-mails
    status = "Servidor MX Ativo ✅"
    ping_ok = False

    if verificar_ping:
        # Tenta o primeiro servidor MX
        ping_ok = ping_servidor_smtp(servidores_mx[0], timeout=2.0)
        if ping_ok:
            status = "Servidor Confirmado ✅"

    return email_limpo, True, status
