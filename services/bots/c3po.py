"""
services/bots/c3po.py
C-3PO: Investigador OSINT via Web Crawling + DuckDuckGo.
Suporta estado por sessao (PipelineState) e logging estruturado.
"""
import threading
import queue
import time
import random
import re
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning

from utils.logger import get_logger

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = get_logger(__name__)


class WorkerC3PO(threading.Thread):
    def __init__(self, callback_log=None, id_robo: int = 1,
                 fila_raw=None, fila_web=None, lock_ativos=None, ativos_agora=None):
        """
        Args:
            callback_log: Funcao de callback para logs na UI
            id_robo: Identificador numerico do worker
            fila_raw: Fila de entrada (PipelineState.fila_raw) - se None usa estado global
            fila_web: Fila de saida (PipelineState.fila_web)
            lock_ativos: Lock para ativos_agora
            ativos_agora: Dict de contagem de workers ativos
        """
        super().__init__(daemon=True)
        self.callback = callback_log
        self.id = id_robo
        self.rodando = True
        self.stats = {
            "lidos": 0, "sites_visitados": 0, "emails_encontrados": 0,
            "cnpjs_encontrados": 0, "erros": 0
        }
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]

        # Suporte a estado por sessao
        if fila_raw is not None:
            self._fila_raw = fila_raw
            self._fila_web = fila_web
            self._lock_ativos = lock_ativos
            self._ativos_agora = ativos_agora
        else:
            from services.state import fila_raw as _fr, fila_web as _fw, lock_ativos as _la, ativos_agora as _aa
            self._fila_raw = _fr
            self._fila_web = _fw
            self._lock_ativos = _la
            self._ativos_agora = _aa

    def get_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session

    def gerar_fallback(self, url: str) -> list[str]:
        """Gera e-mails inferidos se o site for valido."""
        try:
            if not url:
                return []
            dominio = url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if not dominio:
                return []
            dominios_bloqueados = ['instagram.com', 'facebook.com', 'linktr.ee', 'wa.me',
                                   'whatsapp.com', 'youtube.com', 'linkedin.com', 'tiktok.com']
            if any(d in dominio for d in dominios_bloqueados):
                return []
            prefixos = ["contato", "comercial", "atendimento", "vendas", "financeiro", "diretoria"]
            return [f"{p}@{dominio}" for p in prefixos]
        except Exception as e:
            logger.debug(f"Erro em gerar_fallback: {e}")
            return []

    def extrair_contatos_html(self, texto: str, lead: dict) -> None:
        # 1. E-mails
        ignorar = ('.png', '.jpg', 'wixpress', 'sentry', 'example', 'domain',
                   'instagram.com', 'facebook.com', 'wa.me', 'linktr.ee')
        raw_emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto)
        emails_validos = [e.lower() for e in raw_emails
                          if not any(x in e.lower() for x in ignorar) and len(e) > 5]

        if emails_validos:
            if "Emails_Site" not in lead or not isinstance(lead["Emails_Site"], list):
                lead["Emails_Site"] = []
            lead["Emails_Site"].extend(emails_validos)
            lead["Emails_Site"] = list(set(lead["Emails_Site"]))
            self.stats["emails_encontrados"] += len(emails_validos)

        # 2. Telefones
        tels = re.findall(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", texto)
        if tels:
            if "Telefones_Site" not in lead or not isinstance(lead["Telefones_Site"], list):
                lead["Telefones_Site"] = []
            lead["Telefones_Site"].extend(tels)

        # 3. CNPJ
        cnpjs = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
        if cnpjs and not lead.get("CNPJ_Site"):
            lead["CNPJ_Site"] = cnpjs[0]
            self.stats["cnpjs_encontrados"] += 1

        # 4. CEP
        ceps = re.findall(r"\b\d{5}-\d{3}\b", texto)
        if ceps and not lead.get("Endereco Fiscal"):
            lead["Endereco Fiscal"] = f"CEP Encontrado no Site: {ceps[0]}"

    def processar_url(self, url: str, lead: dict, profundidade: int = 0) -> None:
        if profundidade > 1:
            return
        if not url:
            return

        dominios_sociais = ['instagram.com', 'facebook.com', 'linkedin.com']

        # 1. WhatsApp direto
        if "wa.me/" in url or "whatsapp.com" in url or "api.whatsapp.com" in url:
            nums = re.findall(r'\d{10,13}', url)
            if nums:
                if "Telefones_Site" not in lead or not isinstance(lead["Telefones_Site"], list):
                    lead["Telefones_Site"] = []
                lead["Telefones_Site"].append(nums[0])
                if self.callback:
                    self.callback(f"   WhatsApp capturado: {nums[0]}")
            return

        # 2. Rede Social -> DDGS
        if any(d in url for d in dominios_sociais):
            if self.callback:
                self.callback(f"   Rede Social detectada. Analisando via DDGS...")
            try:
                query = f'"{url}"'
                with DDGS() as ddgs:
                    resultados = list(ddgs.text(query, max_results=3))
                    if resultados:
                        texto = " ".join([r.get('body', '') for r in resultados])
                        self.extrair_contatos_html(texto, lead)
                        links_bio = re.findall(r"(https?://[^\s]+)", texto)
                        for link in links_bio:
                            link_clean = link.split(')')[0].split('"')[0]
                            if not any(d in link_clean for d in dominios_sociais):
                                if self.callback:
                                    self.callback(f"   Mergulhando no link da Bio: {link_clean}")
                                lead["Site"] = link_clean
                                self.processar_url(link_clean, lead, profundidade + 1)
                                break
            except Exception as e:
                logger.debug(f"Erro DDGS para {url}: {e}")
            return

        # 3. Site normal -> crawl
        try:
            resp = self.get_session().get(
                url if url.startswith("http") else "http://" + url,
                timeout=10, verify=False
            )
            if resp.status_code < 400:
                self.stats["sites_visitados"] += 1
                soup = BeautifulSoup(resp.text, 'html.parser')
                texto = soup.get_text(" ", strip=True)
                self.extrair_contatos_html(texto, lead)

                if "Emails_Site" not in lead or not lead["Emails_Site"]:
                    emails_inferred = self.gerar_fallback(url)
                    if emails_inferred:
                        lead["Emails_Inferidos"] = emails_inferred
                        if self.callback:
                            self.callback(f"   {len(emails_inferred)} e-mails inferidos gerados.")
            else:
                if profundidade == 0:
                    lead["Site"] = ""
                if self.callback:
                    self.callback(f"   Site fora do ar (Erro {resp.status_code}).")
        except requests.exceptions.RequestException as e:
            logger.debug(f"Erro de conexao para {url}: {e}")
            if profundidade == 0:
                lead["Site"] = ""
            if self.callback:
                self.callback(f"   Link quebrado. Removendo...")
        except Exception as e:
            logger.warning(f"Erro inesperado ao processar URL {url}: {e}", exc_info=True)

    def run(self) -> None:
        if self.callback:
            self.callback(f"C-3PO-{self.id} Online (OSINT via DDGS + Deep Crawling).")

        while self.rodando or not self._fila_raw.empty():
            lead = None
            try:
                lead = self._fila_raw.get(timeout=1)
                with self._lock_ativos:
                    self._ativos_agora["C3PO"] += 1
                self.stats["lidos"] += 1

                url = lead.get("Site")
                empresa = lead.get("Empresa", "")
                cidade = lead.get("Endereco", lead.get("Endereço", ""))

                if self.callback:
                    self.callback(f"C-3PO-{self.id}: Analisando {empresa}...")

                # Busca redes sociais se nao tem site
                if not url or len(str(url)) < 5:
                    if self.callback:
                        self.callback(f"   Sem site. Procurando redes sociais via DDGS...")
                    try:
                        time.sleep(random.uniform(1.5, 3.0))
                        query = f'"{empresa}" "{cidade}" site:instagram.com OR site:facebook.com'
                        with DDGS() as ddgs:
                            resultados = list(ddgs.text(query, max_results=3))
                            for res in resultados:
                                href = res.get('href', '')
                                if 'instagram.com' in href or 'facebook.com' in href:
                                    url = href
                                    lead["Site"] = url
                                    if self.callback:
                                        self.callback(f"   Rede Social encontrada: {url}")
                                    break
                    except Exception as e:
                        logger.debug(f"Erro DDGS busca social para {empresa}: {e}")

                # Mergulho profundo
                if url and len(str(url)) > 5:
                    self.processar_url(url, lead, profundidade=0)

            except queue.Empty:
                continue
            except Exception as e:
                self.stats["erros"] += 1
                logger.error(f"C-3PO-{self.id} erro inesperado: {e}", exc_info=True)
            finally:
                if lead is not None:
                    self._fila_web.put(lead)
                    self._fila_raw.task_done()
                    with self._lock_ativos:
                        self._ativos_agora["C3PO"] -= 1

        relatorio = (
            f"RELATORIO C-3PO-{self.id}:\n"
            f"   - Processados: {self.stats['lidos']}\n"
            f"   - Sites Visitados: {self.stats['sites_visitados']}\n"
            f"   - Emails Encontrados: {self.stats['emails_encontrados']}\n"
            f"   - Erros: {self.stats['erros']}"
        )
        logger.info(relatorio)
        if self.callback:
            self.callback(relatorio)

    def parar(self) -> None:
        self.rodando = False
