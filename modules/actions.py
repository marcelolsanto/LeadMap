"""
modules/actions.py
Acoes humanizadas para o Playwright - versao ASYNC.
"""
import asyncio
import random
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Page
else:
    try:
        from playwright.async_api import Page
    except ImportError:
        Page = Any

logger = logging.getLogger(__name__)


class AcoesHumanas:
    """Simula comportamentos humanos genericos (Versao Assincrona)."""

    @staticmethod
    async def pausa(page: Page, min_s: float = 1.0, max_s: float = 2.0) -> None:
        """Pausa assincrona da execucao."""
        tempo_ms = random.uniform(min_s, max_s) * 1000
        await page.wait_for_timeout(tempo_ms)

    @staticmethod
    async def digitar_no_elemento(page: Page, seletor: str, texto: str, logger_cb=None) -> bool:
        min_s, max_s = 0.1, 0.5
        try:
            if logger_cb:
                logger_cb(f"Pesquisando: '{texto}'...")

            campo = page.locator(seletor)
            await AcoesHumanas.pausa(page, min_s, max_s)
            await campo.click()
            await AcoesHumanas.pausa(page, min_s, max_s)
            await campo.fill("")
            await page.keyboard.type(texto, delay=random.randint(50, 150))
            await AcoesHumanas.pausa(page, min_s, max_s)
            await page.keyboard.press("Enter")
            return True
        except Exception as e:
            logger.error(f"Falha ao digitar '{texto}' no seletor '{seletor}': {e}", exc_info=True)
            return False

    @staticmethod
    async def rolar_feed_bidirecional(page: Page, logger_cb=None) -> bool:
        """Scroll humano com tratamento de erro."""
        min_s, max_s = 1.0, 2.0
        try:
            feed = page.locator("div[role='feed']")
            await feed.hover()
            delta_y = random.randint(2000, 3500)
            await page.mouse.wheel(0, delta_y)
            await AcoesHumanas.pausa(page, min_s, max_s)
            await page.mouse.wheel(0, -random.randint(300, 700))
            await AcoesHumanas.pausa(page, min_s, max_s)
            await page.mouse.wheel(0, delta_y)
            return True
        except Exception as e:
            logger.warning(f"Falha na rolagem do feed: {e}")
            return False

    @staticmethod
    async def interagir_com_mapa(page: Page, logger_cb=None) -> bool:
        """Pan & Zoom no mapa."""
        min_s, max_s = 0.1, 0.5
        try:
            viewport = page.viewport_size
            if not viewport:
                return False
            largura, altura = viewport['width'], viewport['height']
            x_mapa = random.randint(int(largura * 0.3), int(largura * 0.5))
            y_mapa = random.randint(int(altura * 0.3), int(altura * 0.5))
            await page.mouse.move(x_mapa, y_mapa, steps=10)
            await AcoesHumanas.pausa(page, min_s, max_s)
            await page.mouse.wheel(0, random.randint(500, 1000))
            await AcoesHumanas.pausa(page, min_s, max_s)
            await page.mouse.wheel(0, -random.randint(500, 1000))
            await AcoesHumanas.pausa(page, min_s, max_s)
            return True
        except Exception as e:
            logger.warning(f"Falha na interacao com o mapa: {e}")
            return False
