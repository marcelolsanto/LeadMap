"""
scraper/navigator.py
Funcoes de navegacao no Google Maps - versao ASYNC.
"""
import asyncio
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def tentar_fechar_cookies(page: Page) -> None:
    """Tenta fechar o pop-up de consentimento de cookies do Google."""
    botoes = [
        "button[aria-label='Aceitar tudo']",
        "button:has-text('Aceitar tudo')",
        "button:has-text('Aceitar')",
        "button:has-text('Concordo')"
    ]
    for b in botoes:
        try:
            if await page.locator(b).is_visible():
                await page.locator(b).click()
                await asyncio.sleep(1)
                return
        except Exception:
            continue


async def encontrar_caixa_de_busca(page: Page) -> str | None:
    """Tenta encontrar a caixa de busca com tratativa de erros e espera explicita."""
    await tentar_fechar_cookies(page)

    seletores = [
        "input#searchboxinput",
        "input[name='q']",
        "input[aria-label='Pesquisar no Google Maps']",
        "input[class*='searchbox']"
    ]

    for s in seletores:
        try:
            elem = page.locator(s)
            await elem.wait_for(state="visible", timeout=10000)
            return s
        except Exception:
            continue

    logger.error("CRITICO: Caixa de busca nao encontrada.")
    return None


async def verificar_feed_existe(page: Page) -> bool:
    try:
        await page.locator("div[role='feed']").wait_for(state="visible", timeout=5000)
        return True
    except Exception as e:
        logger.error(f"Feed de resultados nao carregou: {e}")
        return False


async def verificar_fim_da_lista(page: Page) -> bool:
    try:
        texto = await page.locator("div[role='feed']").inner_text()
        termos_fim = ["Voce chegou ao final", "Nao ha mais resultados", "Fim da lista",
                      "Você chegou ao final", "Não há mais resultados"]
        return any(msg in texto for msg in termos_fim)
    except Exception:
        return False
