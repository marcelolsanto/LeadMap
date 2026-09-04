"""
services/payment_service.py
Serviço de Verificação de Planos e Pagamentos (PagBank, BTG Pactual e Pix).
"""
from config import settings
from services import repository
from utils.logger import get_logger

logger = get_logger(__name__)


def criar_sessao_checkout(email_usuario: str, tipo_plano: str = "mensal") -> str:
    """
    Retorna o link oficial de pagamento correspondente (PagBank ou BTG).
    """
    logger.info(f"Obtendo link de pagamento para {email_usuario}. Plano: {tipo_plano}")

    if tipo_plano == "anual":
        return getattr(settings, "LINK_PAGAMENTO_ANUAL", "https://pag.ae/827QSc4HM")
    elif tipo_plano == "avulso":

        return getattr(settings, "LINK_PAGAMENTO_AVULSO", "https://links.btgpactual.com/rD8wXVZ0NTPvIOY")
    else:
        return getattr(settings, "LINK_PAGAMENTO_MENSAL", "https://pag.ae/827QRApG9")



def verificar_status_assinatura(email: str) -> bool:
    """
    Verifica se o usuário tem acesso ativo:
    1. Admins e Desenvolvedor (marcelolsantos30@gmail.com) têm acesso livre irrestrito permanente.
    2. Usuário com créditos de consulta avulsa (Pay-per-search) tem acesso liberado para sua busca.
    3. Consulta banco local de assinaturas ativas (Mensal/Anual).
    """
    if not email:
        return False

    email_clean = email.strip().lower()

    # 1. Desenvolvedor e Admins têm acesso livre irrestrito permanente
    admins_lower = [a.strip().lower() for a in getattr(settings, "ADMIN_EMAILS", [])]
    if email_clean == "marcelolsantos30@gmail.com" or email_clean in admins_lower:
        return True

    # 2. Usuário com créditos de consulta avulsa disponíveis (Pay-per-search)
    creditos = repository.obter_creditos_consulta(email_clean)
    if creditos > 0:
        logger.debug(f"Usuário {email_clean} possui {creditos} crédito(s) de consulta avulsa.")
        return True

    # 3. Consulta banco local de assinaturas
    assinatura = repository.consultar_assinatura(email_clean)
    if assinatura:
        status = assinatura.get("status", "")
        if status in ("active", "trialing"):
            logger.debug(f"Assinatura DB: {email_clean} -> {status}")
            return True
        elif status in ("canceled", "past_due", "unpaid"):
            logger.info(f"Assinatura inativa no DB: {email_clean} -> {status}")
            return False

    return False
