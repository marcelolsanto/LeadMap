import pytest
from scraper import parser

# Dados simulados baseados no que o scraper/core.py envia para o parser
TEXTO_BRUTO_MAPS = """
Padaria do Marcelo
4.8 (120) · Padaria
Aberto ⋅ Fecha às 22:00
(11) 99999-8888
Rua das Flores, 123 - São Paulo, SP
Opções de serviço: Compras na loja · Entrega
"""


def test_limpeza_endereco_padrao():
    """
    Testa se a função limpar_endereco remove o nome, telefone e lixo do Google Maps,
    deixando apenas o endereço limpo.
    """
    nome = "Padaria do Marcelo"
    telefone = "(11) 99999-8888"

    # Executa a função real do projeto
    resultado = parser.limpar_endereco(TEXTO_BRUTO_MAPS, nome, telefone)

    # Verificações baseadas na lógica do parser.py
    assert "Rua das Flores, 123 - São Paulo, SP" in resultado
    assert nome not in resultado  # O nome deve ser removido
    assert telefone not in resultado  # O telefone deve ser removido
    assert "Aberto" not in resultado  # Remove status de funcionamento
    assert "Opções de serviço" not in resultado  # Remove metadados


def test_limpeza_endereco_sujo():
    """Testa casos com botões de ação do Maps que o parser deve remover."""
    texto_sujo = """
    Oficina Mecânica
    (11) 98888-7777
    Av. Industrial, 1000 copiar endereço Avaliação
    """
    nome = "Oficina Mecânica"
    telefone = "(11) 98888-7777"

    resultado = parser.limpar_endereco(texto_sujo, nome, telefone)

    assert "Av. Industrial, 1000" in resultado
    assert "copiar endereço" not in resultado  # Regex do parser deve remover isso
    assert "Avaliação" not in resultado
