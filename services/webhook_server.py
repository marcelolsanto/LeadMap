"""
services/webhook_server.py
Servidor Flask para receber eventos do Stripe Webhook.
Roda em thread separada na porta 8502.
"""
import threading
import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

_webhook_thread: threading.Thread | None = None


def _criar_app():
    """Cria e configura o app Flask para o webhook."""
    try:
        from flask import Flask, request, jsonify
        import stripe
        from config import settings
        from services import repository
    except ImportError as e:
        logger.error(f"Dependencia ausente para webhook server: {e}")
        return None

    app = Flask("leadmap_webhook")

    @app.route("/stripe/webhook", methods=["POST"])
    def stripe_webhook():
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get("Stripe-Signature")
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        if not webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET nao configurado. Aceitando evento sem verificacao (apenas em dev).")
            try:
                event = stripe.Event.construct_from(
                    stripe.util.convert_to_stripe_object(request.get_json()),
                    stripe.api_key
                )
            except Exception as e:
                logger.error(f"Erro ao parsear evento Stripe sem assinatura: {e}")
                return jsonify({"error": str(e)}), 400
        else:
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Assinatura Stripe invalida: {e}")
                return jsonify({"error": "Invalid signature"}), 400
            except Exception as e:
                logger.error(f"Erro ao construir evento Stripe: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 400

        event_type = event.get("type", "")
        logger.info(f"Evento Stripe recebido: {event_type}")

        try:
            _processar_evento(event, repository)
        except Exception as e:
            logger.error(f"Erro ao processar evento {event_type}: {e}", exc_info=True)
            return jsonify({"error": "Erro interno"}), 500

        return jsonify({"status": "ok"}), 200

    @app.route("/btg/webhook", methods=["POST"])
    def btg_webhook():
        """Webhook para notificações de PIX do BTG Pactual (evento instant-collection.paid)."""
        try:
            payload = request.get_json(force=True)
            logger.info(f"Webhook BTG Pactual recebido: {payload}")

            # O BTG envia o objeto dentro de data ou no corpo direto
            data_obj = payload.get("data", payload)
            event_type = payload.get("event") or request.headers.get("X-Btg-Event", "")
            status = data_obj.get("status", "")
            tx_id = data_obj.get("txId", "")

            # Eventos oficiais BTG: instant-collection.paid (Pix), payment-link.paid (Cartão/Boleto) e payments.confirmed
            if status in ("PAID", "CONFIRMED") or event_type in ("instant-collection.paid", "payment-link.paid", "payments.confirmed"):
                link_id = data_obj.get("id") or data_obj.get("paymentId", "")
                link_url = data_obj.get("linkUrl", "")
                payer_name = data_obj.get("payer", {}).get("name") or data_obj.get("debitParty", {}).get("name", "Cliente")
                amount = data_obj.get("amount") or data_obj.get("paidAmount", 0)

                logger.info(f"PAGAMENTO BTG CONFIRMADO! Evento: {event_type}, ID: {link_id or tx_id}, Status: {status}, Valor: R$ {amount}")


                # Tenta recuperar o e-mail atrelado à cobrança (via tags, displayText ou payer)
                tags = data_obj.get("tags", {})
                email_comprador = tags.get("email") or tags.get("user") or data_obj.get("displayText")

                if email_comprador and "@" in str(email_comprador):
                    email_clean = str(email_comprador).strip().lower()
                    # Se for o link de consulta avulsa (ou valor avulso):
                    if (link_url and ("xb6gXBfTZ0IMOMa" in link_url or "rD8wXVZ0NTPvIOY" in link_url)) or (amount and float(amount) < 25):
                        repository.adicionar_creditos_consulta(email_clean, 1)

                        logger.info(f"1 Crédito de consulta adicionado via Webhook BTG para {email_clean}")
                    else:
                        repository.salvar_assinatura(
                            email=email_clean,
                            status="active",
                            customer_id="btg_pactual",
                            subscription_id=link_id or tx_id or "btg_link",
                            valido_ate="vitalicio"
                        )
                        logger.info(f"Assinatura ativada via Webhook BTG Pactual para {email_clean}")
                else:
                    logger.info(f"Pagamento BTG recebido de '{payer_name}' (Link: {link_url}).")



            return jsonify({"status": "received"}), 200
        except Exception as e:
            logger.error(f"Erro ao processar Webhook BTG: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 400

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "webhook server online"}), 200


    return app


def _processar_evento(event: dict, repository) -> None:
    """Processa eventos do Stripe e atualiza o banco local."""
    event_type = event.get("type", "")
    data_obj = event.get("data", {}).get("object", {})

    # Mapa de status Stripe -> status interno
    STATUS_MAP = {
        "customer.subscription.created":   "active",
        "customer.subscription.updated":   None,   # usa status do objeto
        "customer.subscription.deleted":   "canceled",
        "invoice.payment_succeeded":        "active",
        "invoice.payment_failed":           "past_due",
    }

    if event_type not in STATUS_MAP:
        logger.debug(f"Evento ignorado: {event_type}")
        return

    # Extrai dados comuns
    customer_id = data_obj.get("customer", "")
    subscription_id = data_obj.get("id") if "subscription" in event_type else data_obj.get("subscription", "")

    # Obtém email do customer
    try:
        import stripe
        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get("email", "")
    except Exception as e:
        logger.error(f"Erro ao recuperar customer {customer_id}: {e}")
        return

    if not email:
        logger.warning(f"Evento {event_type} sem email no customer {customer_id}")
        return

    # Determina o status
    if STATUS_MAP[event_type] is not None:
        status = STATUS_MAP[event_type]
    else:
        status = data_obj.get("status", "unknown")

    # Calcula validade
    valido_ate = ""
    if "current_period_end" in data_obj:
        valido_ate = datetime.datetime.fromtimestamp(
            data_obj["current_period_end"]
        ).strftime("%Y-%m-%d %H:%M:%S")

    repository.salvar_assinatura(
        email=email,
        status=status,
        customer_id=customer_id,
        subscription_id=str(subscription_id),
        valido_ate=valido_ate
    )
    logger.info(f"Assinatura atualizada via webhook: {email} -> {status}")


def iniciar_webhook_server(porta: int = 8502) -> None:
    """
    Inicia o servidor Flask em uma thread daemon.
    Deve ser chamado uma única vez ao iniciar o app.
    """
    global _webhook_thread

    if _webhook_thread and _webhook_thread.is_alive():
        logger.debug("Webhook server ja esta rodando.")
        return

    try:
        from flask import Flask
    except ImportError:
        logger.warning("Flask nao instalado. Webhook server desabilitado.")
        return

    app = _criar_app()
    if not app:
        return

    def _run():
        logger.info(f"Webhook server iniciando na porta {porta}...")
        try:
            app.run(host="0.0.0.0", port=porta, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Erro fatal no webhook server: {e}", exc_info=True)

    _webhook_thread = threading.Thread(target=_run, name="StripeWebhookServer", daemon=True)
    _webhook_thread.start()
    logger.info(f"Webhook server Stripe iniciado em background (porta {porta}).")
