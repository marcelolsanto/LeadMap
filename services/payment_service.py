import stripe
import streamlit as st
from config import settings
from services import repository
from utils.logger import get_logger

logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_API_KEY


def criar_sessao_checkout(email_usuario: str, tipo_plano: str = "mensal") -> str:
    """Cria link de pagamento no Stripe."""
    logger.info(f"Iniciando Checkout para {email_usuario}. Plano: {tipo_plano}")

    if tipo_plano == "anual":
        price_id = settings.STRIPE_PRICE_YEARLY
    else:
        price_id = settings.STRIPE_PRICE_MONTHLY

    if not price_id:
        logger.error("ID do preco nao encontrado em settings.")
        return "#"

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            customer_email=email_usuario,
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{settings.BASE_URL}?payment=success",
            cancel_url=f"{settings.BASE_URL}?payment=cancel",
        )
        return checkout_session.url
    except stripe.error.StripeError as e:
        logger.error(f"Erro Stripe ao criar checkout: {e}", exc_info=True)
        return "#"
    except Exception as e:
        logger.error(f"Erro inesperado no checkout: {e}", exc_info=True)
        return "#"


def verificar_status_assinatura(email: str) -> bool:
    """
    Verifica se o usuário tem assinatura ativa.
    Ordem de verificação:
    1. Admins sempre têm acesso
    2. Consulta banco local (atualizado via Stripe Webhook)
    3. Fallback: consulta direta ao Stripe API
    """
    # 1. Admins têm acesso livre
    if email in settings.ADMIN_EMAILS:
        return True

    # 2. Consulta banco local (preferencial — atualizado pelo webhook)
    assinatura = repository.consultar_assinatura(email)
    if assinatura:
        status = assinatura.get("status", "")
        if status in ("active", "trialing"):
            logger.debug(f"Assinatura DB: {email} -> {status}")
            return True
        elif status in ("canceled", "past_due", "unpaid"):
            logger.info(f"Assinatura inativa no DB: {email} -> {status}")
            return False

    # 3. Fallback: consulta direta ao Stripe (quando webhook ainda nao processou)
    if settings.STRIPE_API_KEY:
        try:
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                customer = customers.data[0]
                subscriptions = stripe.Subscription.list(
                    customer=customer.id,
                    status="active",
                    limit=1
                )
                if subscriptions.data:
                    sub = subscriptions.data[0]
                    # Sincroniza com banco local
                    import datetime
                    valido_ate = datetime.datetime.fromtimestamp(
                        sub.current_period_end
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    repository.salvar_assinatura(
                        email=email,
                        status="active",
                        customer_id=customer.id,
                        subscription_id=sub.id,
                        valido_ate=valido_ate
                    )
                    return True
        except stripe.error.StripeError as e:
            logger.warning(f"Erro ao consultar Stripe para {email}: {e}")
        except Exception as e:
            logger.warning(f"Erro inesperado ao consultar Stripe: {e}")

    return False
