import pytest
from services.bots.walle import WorkerWallE


def test_formatar_telefone_valido():
    worker = WorkerWallE(id_robo=99)
    assert worker.formatar_telefone("11999998888") == "+5511999998888"
    assert worker.formatar_telefone("(11) 99999-8888") == "+5511999998888"
    assert worker.formatar_telefone("011999998888") == "+5511999998888"
    assert worker.formatar_telefone("+55 11 99999-8888") == "+5511999998888"


def test_formatar_telefone_invalido():
    worker = WorkerWallE(id_robo=99)
    assert worker.formatar_telefone("") is None
    assert worker.formatar_telefone(None) is None
    assert worker.formatar_telefone("123") is None


def test_validar_email_valido():
    worker = WorkerWallE(id_robo=99)
    assert worker.validar_email("contato@empresa.com.br") == "contato@empresa.com.br"
    assert worker.validar_email("  ADMIN@EMPRESA.COM  ") == "admin@empresa.com"


def test_validar_email_bloqueado():
    worker = WorkerWallE(id_robo=99)
    assert worker.validar_email("noreply@empresa.com") is None
    assert worker.validar_email("sentry@wix.com") is None
    assert worker.validar_email("logo.png@domain.com") is None
    assert worker.validar_email("user@instagram.com") is None
    assert worker.validar_email(None) is None
    assert worker.validar_email("invalido") is None


def test_eleger_melhor_contato_hibrido():
    worker = WorkerWallE(id_robo=99)
    lead_entrada = {
        "Empresa": "Empresa Teste",
        "Telefone": "(11) 98888-7777",
        "Telefone_Fiscal": "(11) 99999-0000",
        "Endereco": "Rua Maps, 100",
        "Endereco Fiscal": "Av Fiscal Oficial, 500 - Centro, SP",
        "Site": "https://empresateste.com.br",
        "Email_Fiscal": "fiscal@empresateste.com.br",
        "Emails_Site": ["contato@empresateste.com.br"]
    }

    resultado = worker.eleger_melhor_contato(lead_entrada)

    # Prioriza endereco fiscal
    assert "Av Fiscal Oficial" in resultado["Endereço"]
    # Prioriza email fiscal
    assert resultado["Email"] == "fiscal@empresateste.com.br"
    # Formata telefone
    assert resultado["Telefone"] == "+5511999990000"
    # Identifica tipo de link
    assert resultado["Tipo_Link"] == "Site Oficial"
