import asyncio
from unittest.mock import MagicMock
from modules.actions import AcoesHumanas


def test_digitar_com_erro():
    page_mock = MagicMock()
    page_mock.locator.side_effect = Exception("Elemento nao encontrado")

    sucesso = asyncio.run(AcoesHumanas.digitar_no_elemento(page_mock, "#busca", "Padaria"))
    assert sucesso is False
