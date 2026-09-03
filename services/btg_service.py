"""
services/btg_service.py
Integração com BTG Pactual Empresas (API Pix Cash-In e Gerador Pix EMVCo Banco Central).
"""
import base64
import requests
import urllib.parse
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


BTG_TOKEN_FILE = ".btg_token.json"


def gerar_link_autorizacao_btg(redirect_uri: str = None) -> str:
    """
    Gera a URL do fluxo Authorization Code para autorizar a aplicação no BTG Pactual Id.
    Escopos exigidos pela documentação oficial: openid e empresas.btgpactual.com/pix-cash-in.
    """
    base = "https://id.btgpactual.com/oauth2/authorize"
    r_uri = redirect_uri or getattr(settings, "REDIRECT_URI", "http://localhost:8501")
    client_id = getattr(settings, "BTG_CLIENT_ID", "b8bc88f5-7461-4817-b3d3-cd8a23edf6b8")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": r_uri,
        "scope": "openid brn:btg:empresas:payment-link empresas.btgpactual.com/pix-cash-in"
    }
    return f"{base}?{urllib.parse.urlencode(params)}"



def trocar_codigo_por_token_btg(auth_code: str, redirect_uri: str = None) -> dict | None:
    """
    Troca o código de autorização gerado no navegador pelos tokens de acesso e refresh.
    Salva o token localmente para renovação contínua.
    """
    client_id = getattr(settings, "BTG_CLIENT_ID", None)
    client_secret = getattr(settings, "BTG_CLIENT_SECRET", None)
    r_uri = redirect_uri or getattr(settings, "REDIRECT_URI", "http://localhost:8501")

    if not client_id or not client_secret:
        return None

    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": r_uri
    }

    try:
        r = requests.post("https://id.btgpactual.com/oauth2/token", headers=headers, data=data, timeout=8)
        if r.status_code == 200:
            token_data = r.json()
            with open(BTG_TOKEN_FILE, "w") as f:
                import json
                json.dump(token_data, f)
            logger.info("Tokens BTG Pactual obtidos e salvos com sucesso.")
            return token_data
        else:
            logger.error(f"Erro ao trocar código por token BTG ({r.status_code}): {r.text}")
            return None
    except Exception as e:
        logger.error(f"Falha na comunicação com BTG: {e}", exc_info=True)
        return None


def obter_token_btg() -> str | None:
    """
    Recupera o access_token válido do BTG Pactual (lê do arquivo salvo ou tenta renovar).
    """
    import os, json
    if os.path.exists(BTG_TOKEN_FILE):
        try:
            with open(BTG_TOKEN_FILE, "r") as f:
                saved = json.load(f)
                return saved.get("access_token")
        except Exception:
            pass
    return None



# ─── GERADOR PIX EMVCO DO BANCO CENTRAL (COMPATÍVEL COM TODOS OS BANCOS) ─────

def _crc16_ccitt(data: str) -> str:
    """Calcula checksum CRC16-CCITT exigido pela especificação do Banco Central."""
    poly = 0x1021
    crc = 0xFFFF
    for b in data.encode("utf-8"):
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _format_field(id_str: str, val: str) -> str:
    return f"{id_str}{len(val):02d}{val}"


def gerar_pix_copia_cola(
    valor: float,
    chave: str = None,
    nome: str = None,
    cidade: str = None,
    txid: str = "LEADMAP"
) -> str:
    """
    Gera o código oficial 'Pix Copia e Cola' (BRCode EMVCo).
    Compatível com BTG Pactual, Nubank, Itaú, Bradesco, Inter, etc.
    """
    chave_raw = (chave or getattr(settings, "BTG_PIX_CHAVE", "62977131000180")).strip()
    # Se a chave for CNPJ ou CPF ou telefone com pontuação, remove formatação
    if "/" in chave_raw or "-" in chave_raw or "." in chave_raw:
        digitos = "".join(c for c in chave_raw if c.isdigit())
        if len(digitos) in (11, 14):
            chave_pix = digitos
        else:
            chave_pix = chave_raw
    else:
        chave_pix = chave_raw

    beneficiario = nome or getattr(settings, "BTG_BENEFICIARIO_NOME", "MARCELO SANTOS")
    cidade_pix = cidade or getattr(settings, "BTG_BENEFICIARIO_CIDADE", "BRASILIA")

    # Merchant Account Info (ID 26)
    gui = _format_field("00", "br.gov.bcb.pix")
    key = _format_field("01", chave_pix)
    mai = _format_field("26", gui + key)

    # Payload Format
    pfi = _format_field("00", "01")
    mcc = _format_field("52", "0400")
    curr = _format_field("53", "986")  # BRL (Real)
    amt = _format_field("54", f"{valor:.2f}")
    cc = _format_field("58", "BR")
    mname = _format_field("59", beneficiario[:25])
    mcity = _format_field("60", cidade_pix[:15])

    # Additional Data (ID 62)
    tx = _format_field("05", txid[:25])
    add_data = _format_field("62", tx)

    raw = pfi + mai + mcc + curr + amt + cc + mname + mcity + add_data + "6304"
    checksum = _crc16_ccitt(raw)
    return raw + checksum


def gerar_qr_code_url(pix_code: str) -> str:
    """Gera link de imagem do QR Code para exibição visual na tela."""
    encoded = urllib.parse.quote(pix_code)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded}"
