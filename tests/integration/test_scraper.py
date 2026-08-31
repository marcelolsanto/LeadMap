import pytest
from unittest.mock import MagicMock, patch
from scraper.core import GoogleMapsScraper


@patch('scraper.core.sync_playwright')
@patch('scraper.core.os')  # Mock para não criar pastas reais durante o teste
def test_inicializacao_scraper(mock_os, mock_playwright):
    """
    Verifica se o Scraper inicializa as variáveis corretamente de acordo
    com o código atual do projeto.
    """
    termo = "Padaria em SP"
    scraper = GoogleMapsScraper(termo)

    assert scraper.termo == termo
    # No seu código original, não existe self.leads, mas sim self.total_enviado
    assert scraper.total_enviado == 0
    # Verifica se o auxiliar de ações humanas foi iniciado
    assert scraper.humano is not None


@patch('scraper.core.sync_playwright')
@patch('scraper.core.navigator')  # Mock do navigator para controlar o fluxo
@patch('scraper.core.os')
def test_argumentos_browser_no_rodar(mock_os, mock_navigator, mock_playwright):
    """
    Testa indiretamente se o browser é lançado com os argumentos corretos.
    Como a lógica está dentro de 'rodar', simulamos o fluxo até a abertura do browser
    e forçamos uma saída limpa antes do loop de extração.
    """
    # 1. Configura o Mock do Playwright
    mock_p = MagicMock()
    mock_playwright.return_value.__enter__.return_value = mock_p

    # 2. Configura o Mock do Navigator para abortar a missão cedo
    # Faz o 'encontrar_caixa_de_busca' retornar None.
    # Isso faz o seu código entrar no 'if not seletor: return' (linha 786 do core.py)
    # Assim, testamos a configuração do browser sem rodar o scraper inteiro.
    mock_navigator.encontrar_caixa_de_busca.return_value = None

    # 3. Executa
    scraper = GoogleMapsScraper("Teste")
    scraper.rodar()

    # 4. Verificações
    # Verifica se chamou launch_persistent_context (usado no seu código)
    mock_p.chromium.launch_persistent_context.assert_called_once()

    # Pega os argumentos que foram passados para o browser
    _, kwargs = mock_p.chromium.launch_persistent_context.call_args

    # Valida as configurações críticas do seu projeto
    assert kwargs['headless'] is False  # Seu código está hardcoded como False
    assert "--disable-blink-features=AutomationControlled" in kwargs['args']
    assert "--start-maximized" in kwargs['args']
