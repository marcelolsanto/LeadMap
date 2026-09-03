from config import settings
from services import repository
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import stripe
    stripe.api_key = getattr(settings, 'STRIPE_API_KEY', None)
except ImportError:
    stripe = None




def criar_sessao_checkout(email_usuario: str, tipo_plano: str = "mensal") -> str:
    """
    Cria ou retorna link de pagamento do Stripe para Cartão ou PIX.
    Suporta links diretos (STRIPE_CHECKOUT_URL_*) ou criação dinâmica via API.
    """
    logger.info(f"Iniciando Checkout para {email_usuario}. Plano: {tipo_plano}")

    # 1. Verifica se há link direto de pagamento configurado
    if tipo_plano == "anual" and getattr(settings, 'STRIPE_CHECKOUT_URL_YEARLY', None):
        link = settings.STRIPE_CHECKOUT_URL_YEARLY
        if email_usuario and "?" not in link:
            return f"{link}?prefilled_email={email_usuario}"
        return link
    elif tipo_plano == "mensal" and getattr(settings, 'STRIPE_CHECKOUT_URL_MONTHLY', None):
        link = settings.STRIPE_CHECKOUT_URL_MONTHLY
        if email_usuario and "?" not in link:
            return f"{link}?prefilled_email={email_usuario}"
        return link

    # 2. Criação de sessão via API Stripe
    if tipo_plano == "anual":
        price_id = getattr(settings, 'STRIPE_PRICE_YEARLY', None)
    else:
        price_id = getattr(settings, 'STRIPE_PRICE_MONTHLY', None)

    if not price_id or not settings.STRIPE_API_KEY:
        logger.warning(f"Chave Stripe ou Price ID ({tipo_plano}) não configurados.")
        return "#"

    try:
        # Se suportado pela conta Stripe, permite cartão e boleto
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card', 'boleto'],
            customer_email=email_usuario,
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{settings.BASE_URL}?payment=success&email={email_usuario}",
            cancel_url=f"{settings.BASE_URL}?payment=cancel",
        )
        return checkout_session.url
    except stripe.error.StripeError as e:
        # Fallback apenas para cartão caso boleto não esteja ativado na conta Stripe
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=email_usuario,
                line_items=[{'price': price_id, 'quantity': 1}],
                mode='subscription',
                success_url=f"{settings.BASE_URL}?payment=success&email={email_usuario}",
                cancel_url=f"{settings.BASE_URL}?payment=cancel",
            )
            return checkout_session.url
        except Exception as e2:
            logger.error(f"Erro Stripe ao criar checkout: {e2}", exc_info=True)
            return "#"
    except Exception as e:
        logger.error(f"Erro inesperado no checkout: {e}", exc_info=True)
        return "#"


def verificar_status_assinatura(email: str) -> bool:
    """
    Verifica se o usuário tem assinatura ativa.
    Ordem de verificação:
    1. Admins e Desenvolvedor (marcelolsantos30@gmail.com) têm acesso livre irrestrito sem plano.
    2. Consulta banco local (atualizado via Stripe Webhook ou Checkout)
    3. Fallback: consulta direta ao Stripe API
    """
    if not email:
        return False

    email_clean = email.strip().lower()

    # 1. Desenvolvedor e Admins têm acesso livre irrestrito permanente
    admins_lower = [a.strip().lower() for a in getattr(settings, 'ADMIN_EMAILS', [])]
    if email_clean == "marcelolsantos30@gmail.com" or email_clean in admins_lower:
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
