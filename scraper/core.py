"""
scraper/core.py
BB-8: Extrator do Google Maps - versao ASYNC com playwright.async_api.
"""
import asyncio
import os
import re
import logging
import urllib.parse
from datetime import datetime
from playwright.async_api import async_playwright

from config import settings
from modules.actions import AcoesHumanas
from scraper import navigator, parser
from modules.stealth import stealth_sync
from utils.logger import get_logger

logger = get_logger(__name__)


class GoogleMapsScraper:
    def __init__(self, termo_busca: str, callback_log=None,
                 fila_raw=None, estatisticas=None, status_pipeline=None):
        """
        Args:
            termo_busca: Termo de busca no Google Maps
            callback_log: Funcao de callback para logs na UI
            fila_raw: Fila de saida (PipelineState.fila_raw) - se None, usa state global legado
            estatisticas: Dict de metricas (PipelineState.estatisticas)
            status_pipeline: Dict de status (PipelineState.status_pipeline)
        """
        self.termo = termo_busca
        self.callback_log = callback_log
        self.humano = AcoesHumanas()
        self.total_enviado = 0

        # Suporte a estado por sessao (novo) ou estado global (legado)
        if fila_raw is not None:
            self._fila_raw = fila_raw
            self._estatisticas = estatisticas
            self._status_pipeline = status_pipeline
        else:
            # Compatibilidade retroativa com estado global
            from services.state import fila_raw as _fr, estatisticas as _e, status_pipeline as _sp
            self._fila_raw = _fr
            self._estatisticas = _e
            self._status_pipeline = _sp

    def log(self, msg: str) -> None:
        if self.callback_log:
            self.callback_log(msg)

    async def rodar(self) -> None:
        """Executa o scraping de forma assincrona."""
        caminho_perfil = os.path.abspath("perfil_chrome")
        if not os.path.exists(caminho_perfil):
            os.makedirs(caminho_perfil)

        # Limpa trava do Chrome
        try:
            lock = os.path.join(caminho_perfil, "SingletonLock")
            if os.path.exists(lock):
                os.remove(lock)
        except Exception as e:
            logger.warning(f"Erro ao remover SingletonLock: {e}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=caminho_perfil,
                    headless=True,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                    viewport=None
                )

                page = browser.pages[0] if browser.pages else await browser.new_page()

                # Aplica stealth (modo sync - ainda compativel via sync call no contexto async)
                try:
                    stealth_sync(page)
                except Exception as e:
                    logger.warning(f"Stealth nao aplicado: {e}")

                self.log(f"Iniciando: {self.termo}")
                await page.goto("https://www.google.com.br/maps", timeout=60000)

                seletor = await navigator.encontrar_caixa_de_busca(page)
                if not seletor:
                    self.log("Erro Critico: Nao achei a caixa de busca.")
                    return

                await self.humano.digitar_no_elemento(page, seletor, self.termo, self.log)

                if not await navigator.verificar_feed_existe(page):
                    self.log("Lista nao carregou.")
                    return

                tentativa = 0
                altura_ant = 0
                unicos: set[str] = set()

                while tentativa < 300:
                    tentativa += 1
                    await self.humano.rolar_feed_bidirecional(page)

                    cards = await page.locator("div[role='feed'] > div").all()
                    count_novos = 0

                    for card in cards:
                        try:
                            txt = await card.inner_text()
                            if len(txt) < 10 or "Anuncio" in txt or "Patrocinado" in txt:
                                continue

                            tels = re.findall(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", txt)
                            if tels:
                                tel = tels[0]
                                nome = txt.split('\n')[0]
                                chave = f"{nome}_{tel}"

                                if chave not in unicos:
                                    site_url = ""
                                    instagram = ""
                                    facebook = ""
                                    linkedin = ""

                                    try:
                                        links = await card.locator("a").all()
                                        for l in links:
                                            h = await l.get_attribute("href")
                                            if not h:
                                                continue
                                            if "/maps/" in h or "google.com/search" in h:
                                                continue
                                            if "instagram.com" in h:
                                                instagram = h
                                                continue
                                            elif "facebook.com" in h or "fb.com" in h:
                                                facebook = h
                                                continue
                                            elif "linkedin.com" in h:
                                                linkedin = h
                                                continue
                                            if "google.com/url" in h:
                                                parsed = urllib.parse.urlparse(h)
                                                qs = urllib.parse.parse_qs(parsed.query)
                                                url_real = qs.get('q', qs.get('url', [None]))[0]
                                                if url_real and not site_url:
                                                    site_url = url_real
                                            elif h.startswith("http") and "google.com" not in h and not site_url:
                                                site_url = h
                                    except Exception as e:
                                        logger.debug(f"Erro ao extrair links do card: {e}")

                                    lead = {
                                        "Empresa": nome,
                                        "Telefone": tel,
                                        "Endereco": parser.limpar_endereco(txt, nome, tel),
                                        "Site": site_url,
                                        "Instagram_Maps": instagram,
                                        "Facebook_Maps": facebook,
                                        "LinkedIn_Maps": linkedin,
                                        "Data": datetime.now().strftime("%d/%m/%Y")
                                    }

                                    self._fila_raw.put(lead)
                                    unicos.add(chave)
                                    self.total_enviado += 1
                                    count_novos += 1
                                    if self._estatisticas is not None:
                                        self._estatisticas["total_bb8"] += 1

                        except Exception as e:
                            logger.debug(f"Erro ao processar card: {e}")
                            continue

                    if count_novos > 0:
                        self.log(f"{count_novos} novos alvos detectados.")

                    try:
                        c = await page.locator("div[role='feed'] > div").count()
                        if c == altura_ant:
                            tentativa += 20
                        altura_ant = c
                    except Exception as e:
                        logger.debug(f"Erro ao contar cards: {e}")

                    if await navigator.verificar_fim_da_lista(page):
                        break

                self.log("Fechando o navegador.")
                await browser.close()

        except Exception as e:
            logger.error(f"Erro fatal no BB-8: {e}", exc_info=True)
            self.log(f"Erro fatal no BB-8: {e}")
        finally:
            if self._status_pipeline is not None:
                self._status_pipeline["bb8_terminou"] = True
            self.log("BB-8 retornou a base. Busca no mapa concluida.")
