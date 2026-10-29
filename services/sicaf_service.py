"""
services/sicaf_service.py
Módulo de Integração com a API de Dados Abertos do Compras.gov.br (SICAF / Governo Federal).
Permite verificar em tempo real se um CNPJ é fornecedor credenciado do Governo Federal,
se possui habilitação jurídica/fiscal ativa para licitar e seu porte oficial cadastrado.
"""
import re
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

COMPRAS_API_URL = "https://dadosabertos.compras.gov.br/modulo-fornecedor/1_consultarFornecedor"


def consultar_sicaf(cnpj: str, timeout: float = 6.0) -> dict:
    """
    Consulta o CNPJ na API pública do Compras.gov.br / SICAF.

    Retorna um dicionário padronizado:
    {
        "sicaf_ativo": bool,
        "habilitado_licitar": bool,
        "porte_sicaf": str,
        "razao_social_sicaf": str,
        "cnae_sicaf": str,
        "municipio_sicaf": str,
        "uf_sicaf": str
    }
    """
    nums = re.sub(r'\D', '', str(cnpj or ''))
    if len(nums) != 14:
        return {
            "sicaf_ativo": False,
            "habilitado_licitar": False,
            "porte_sicaf": "Não cadastrado",
            "razao_social_sicaf": "",
            "cnae_sicaf": "",
            "municipio_sicaf": "",
            "uf_sicaf": ""
        }

    params = {
        "cnpj": nums,
        "ativo": "true",
        "pagina": 1,
        "tamanhoPagina": 10
    }

    try:
        response = requests.get(
            COMPRAS_API_URL,
            params=params,
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "LeadMap-Pro-Enrichment/4.2"
            }
        )

        if response.status_code == 200:
            dados = response.json()
            resultado = dados.get("resultado", [])
            if resultado and len(resultado) > 0:
                item = resultado[0]
                return {
                    "sicaf_ativo": bool(item.get("ativo", True)),
                    "habilitado_licitar": bool(item.get("habilitadoLicitar", False)),
                    "porte_sicaf": str(item.get("porteEmpresaNome") or "DEMAIS"),
                    "razao_social_sicaf": str(item.get("nomeRazaoSocialFornecedor") or ""),
                    "cnae_sicaf": str(item.get("nomeCnae") or ""),
                    "municipio_sicaf": str(item.get("nomeMunicipio") or ""),
                    "uf_sicaf": str(item.get("ufSigla") or "")
                }

        # Não localizado ou status diferente de 200
        return {
            "sicaf_ativo": False,
            "habilitado_licitar": False,
            "porte_sicaf": "Não cadastrado",
            "razao_social_sicaf": "",
            "cnae_sicaf": "",
            "municipio_sicaf": "",
            "uf_sicaf": ""
        }

    except requests.exceptions.Timeout:
        logger.debug(f"Timeout ao consultar SICAF para CNPJ {nums}")
    except requests.exceptions.RequestException as e:
        logger.debug(f"Falha de rede ao consultar SICAF para CNPJ {nums}: {e}")
    except Exception as e:
        logger.warning(f"Erro inesperado no sicaf_service para CNPJ {nums}: {e}")

    return {
        "sicaf_ativo": False,
        "habilitado_licitar": False,
        "porte_sicaf": "Erro de consulta",
        "razao_social_sicaf": "",
        "cnae_sicaf": "",
        "municipio_sicaf": "",
        "uf_sicaf": ""
    }
