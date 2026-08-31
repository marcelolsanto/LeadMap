import requests
import re
from utils.logger import get_logger

logger = get_logger(__name__)


def limpar_cnpj(cnpj_bruto: str) -> str:
    """Remove pontos, barras e tracos."""
    if not cnpj_bruto:
        return ""
    return re.sub(r'\D', '', str(cnpj_bruto))


def consultar_empresa(cnpj: str) -> dict | None:
    """
    Consulta dados avancados na BrasilAPI (Gratuita).
    Retorna endereco completo, CEP e E-mail fiscal.
    """
    cnpj_limpo = limpar_cnpj(cnpj)

    if len(cnpj_limpo) != 14:
        return None

    try:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            dados = response.json()

            logradouro = dados.get("logradouro", "")
            numero = dados.get("numero", "")
            bairro = dados.get("bairro", "")
            municipio = dados.get("municipio", "")
            uf = dados.get("uf", "")
            cep = dados.get("cep", "")

            endereco_fiscal = f"{logradouro}, {numero} - {bairro}, {municipio} - {uf}"

            tel_fiscal = None
            if dados.get("ddd_telefone_1") and dados.get("telefone_1"):
                tel_fiscal = f"({dados.get('ddd_telefone_1')}) {dados.get('telefone_1')}"
            elif dados.get("telefone_1"):
                tel_fiscal = dados.get("telefone_1")

            return {
                "razao_social": dados.get("razao_social", ""),
                "nome_fantasia": dados.get("nome_fantasia", ""),
                "situacao": dados.get("situacao_cadastral", ""),
                "cnae": dados.get("cnae_fiscal_descricao", ""),
                "email_fiscal": dados.get("email", ""),
                "telefone_fiscal": tel_fiscal,
                "endereco_fiscal": endereco_fiscal,
                "cep": cep
            }
        else:
            logger.debug(f"BrasilAPI status {response.status_code} para CNPJ {cnpj_limpo}")
            return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Erro de conexao BrasilAPI CNPJ {cnpj_limpo}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao consultar BrasilAPI CNPJ {cnpj_limpo}: {e}", exc_info=True)
        return None
