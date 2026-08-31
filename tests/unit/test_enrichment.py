from unittest.mock import patch, MagicMock
from services import enrichment_service


def test_limpar_cnpj():
    assert enrichment_service.limpar_cnpj("12.345.678/0001-90") == "12345678000190"
    assert enrichment_service.limpar_cnpj("12345678000190") == "12345678000190"
    assert enrichment_service.limpar_cnpj("") == ""
    assert enrichment_service.limpar_cnpj(None) == ""


@patch("services.enrichment_service.requests.get")
def test_consultar_empresa_sucesso(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "razao_social": "EMPRESA TESTE LTDA",
        "nome_fantasia": "EMPRESA TESTE",
        "situacao_cadastral": "ATIVA",
        "cnae_fiscal_descricao": "Desenvolvimento de Software",
        "email": "contato@empresateste.com.br",
        "ddd_telefone_1": "11",
        "telefone_1": "999998888",
        "logradouro": "RUA TESTE",
        "numero": "100",
        "bairro": "CENTRO",
        "municipio": "SAO PAULO",
        "uf": "SP",
        "cep": "01000-000"
    }
    mock_get.return_value = mock_response

    resultado = enrichment_service.consultar_empresa("12.345.678/0001-90")

    assert resultado is not None
    assert resultado["razao_social"] == "EMPRESA TESTE LTDA"
    assert resultado["email_fiscal"] == "contato@empresateste.com.br"
    assert resultado["telefone_fiscal"] == "(11) 999998888"
    assert "RUA TESTE, 100" in resultado["endereco_fiscal"]
    assert resultado["situacao"] == "ATIVA"


def test_consultar_empresa_cnpj_invalido():
    resultado = enrichment_service.consultar_empresa("123")
    assert resultado is None
