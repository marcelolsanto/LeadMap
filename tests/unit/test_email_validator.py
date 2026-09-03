import pytest
from services.email_validator import (
    validar_sintaxe_email,
    obter_servidores_mx,
    validar_email_completo
)


def test_validar_sintaxe_valida():
    assert validar_sintaxe_email("contato@empresa.com.br") == "contato@empresa.com.br"
    assert validar_sintaxe_email("FINANCEIRO@EMPRESA.COM.BR") == "financeiro@empresa.com.br"


def test_validar_sintaxe_blacklist():
    assert validar_sintaxe_email("noreply@site.com") is None
    assert validar_sintaxe_email("imagem.png@site.com") is None
    assert validar_sintaxe_email("contato@instagram.com") is None
    assert validar_sintaxe_email("invalido") is None


def test_obter_servidores_mx_real():
    mx_list = obter_servidores_mx("gmail.com")
    assert len(mx_list) > 0
    assert any("google" in mx.lower() for mx in mx_list)


def test_validar_email_completo_dominio_inexistente():
    email, valido, msg = validar_email_completo("contato@dominio_inexistente_leadmap_999999.com", verificar_ping=False)
    assert email is None
    assert valido is False


def test_validar_email_completo_dominio_valido():
    email, valido, msg = validar_email_completo("suporte@google.com", verificar_ping=False)
    assert email == "suporte@google.com"
    assert valido is True
    assert "Servidor" in msg

