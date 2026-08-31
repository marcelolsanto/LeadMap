import re
import requests
import logging


def extrair_dados_site(url_site):
    """
    Acessa o site e tenta encontrar e-mails e CNPJ na página inicial.
    Retorna um dicionário com os dados encontrados.
    """
    dados = {"emails": "", "cnpj": ""}

    if not url_site:
        return dados

    if not url_site.startswith("http"):
        url_site = "http://" + url_site

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Timeout curto para não travar o robô
        response = requests.get(url_site, headers=headers, timeout=5)

        if response.status_code == 200:
            texto = response.text

            # 1. Extração de E-mails
            emails_brutos = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto))
            ignorar = ['.png', '.jpg', '.js', '.css', 'wixpress', 'sentry', 'example', 'domain', 'email']
            emails_limpos = [e.lower() for e in emails_brutos if not any(x in e.lower() for x in ignorar)]
            dados["emails"] = ", ".join(emails_limpos[:2])

            # 2. Extração de CNPJ (Novo!)
            # Procura pelo padrão XX.XXX.XXX/XXXX-XX
            cnpjs = set(re.findall(r"\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}", texto))
            if cnpjs:
                dados["cnpj"] = list(cnpjs)[0]  # Pega o primeiro encontrado

    except Exception as e:
        logging.warning(f"Erro ao ler site {url_site}: {e}")

    return dados
