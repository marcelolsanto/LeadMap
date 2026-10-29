from unittest.mock import patch, MagicMock
from services import sicaf_service


def test_consultar_sicaf_cnpj_invalido():
    res = sicaf_service.consultar_sicaf("123")
    assert res["sicaf_ativo"] is False
    assert res["porte_sicaf"] == "Não cadastrado"


@patch("services.sicaf_service.requests.get")
def test_consultar_sicaf_cadastrado_e_habilitado(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "resultado": [
            {
                "ativo": True,
                "cnpj": "57142978000105",
                "habilitadoLicitar": True,
                "codigoCnae": 6203100,
                "nomeCnae": "DESENVOLVIMENTO DE SOFTWARE",
                "naturezaJuridicaNome": "SOCIEDADE EMPRESARIA LIMITADA",
                "porteEmpresaNome": "DEMAIS",
                "nomeRazaoSocialFornecedor": "BRASOFTWARE INFORMATICA LTDA",
                "nomeMunicipio": "POA",
                "ufSigla": "SP"
            }
        ],
        "totalRegistros": 1
    }
    mock_get.return_value = mock_resp

    res = sicaf_service.consultar_sicaf("57.142.978/0001-05")

    assert res["sicaf_ativo"] is True
    assert res["habilitado_licitar"] is True
    assert res["porte_sicaf"] == "DEMAIS"
    assert res["razao_social_sicaf"] == "BRASOFTWARE INFORMATICA LTDA"
    assert res["uf_sicaf"] == "SP"


@patch("services.sicaf_service.requests.get")
def test_consultar_sicaf_nao_cadastrado(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "resultado": [],
        "totalRegistros": 0
    }
    mock_get.return_value = mock_resp

    res = sicaf_service.consultar_sicaf("11.111.111/0001-99")

    assert res["sicaf_ativo"] is False
    assert res["habilitado_licitar"] is False
    assert res["porte_sicaf"] == "Não cadastrado"


@patch("services.sicaf_service.requests.get")
def test_consultar_sicaf_erro_rede(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("Timeout teste")

    res = sicaf_service.consultar_sicaf("57.142.978/0001-05")

    assert res["sicaf_ativo"] is False
    assert res["habilitado_licitar"] is False
    assert res["porte_sicaf"] == "Erro de consulta"
