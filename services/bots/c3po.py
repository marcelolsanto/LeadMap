"""
services/bots/c3po.py
C-3PO: Investigador OSINT com Deep Web Crawling, Redes Sociais e Mineração de Buscas.
Suporta estado por sessão (PipelineState) e logging estruturado.
"""
import threading
import queue
import time
import random
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

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
            callback_log: Função de callback para logs na UI
            id_robo: Identificador numérico do worker
            fila_raw: Fila de entrada (PipelineState.fila_raw)
            fila_web: Fila de saída (PipelineState.fila_web)
            lock_ativos: Lock para ativos_agora
            ativos_agora: Dict de contagem de workers ativos
        """
        super().__init__(daemon=True)
        self.callback = callback_log
        self.id = id_robo
        self.rodando = True
        self.stats = {
            "lidos": 0, "sites_visitados": 0, "emails_encontrados": 0,
            "cnpjs_encontrados": 0, "redes_sociais": 0, "erros": 0
        }
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0'
        ]

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
        """Gera e-mails inferidos se o site for válido."""
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

    def extrair_contatos_html(self, soup: BeautifulSoup, texto: str, url_base: str, lead: dict) -> None:
        """Extrai telefones, e-mails, CNPJs, WhatsApp e links de redes sociais do HTML."""
        ignorar_emails = ('.png', '.jpg', '.jpeg', '.webp', '.svg', '.js', '.css',
                          'wixpress', 'sentry', 'example', 'domain', 'instagram.com',
                          'facebook.com', 'wa.me', 'linktr.ee')

        # 1. E-mails no texto e em links mailto:
        emails_encontrados = set()
        for e in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", texto):
            if not any(x in e.lower() for x in ignorar_emails) and len(e) > 5:
                emails_encontrados.add(e.lower().strip())

        if soup:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                if href.lower().startswith('mailto:'):
                    email_clean = href.replace('mailto:', '').split('?')[0].strip().lower()
                    if "@" in email_clean and not any(x in email_clean for x in ignorar_emails):
                        emails_encontrados.add(email_clean)

        if emails_encontrados:
            if "Emails_Site" not in lead or not isinstance(lead["Emails_Site"], list):
                lead["Emails_Site"] = []
            lead["Emails_Site"].extend(list(emails_encontrados))
            lead["Emails_Site"] = list(set(lead["Emails_Site"]))
            self.stats["emails_encontrados"] += len(emails_encontrados)

        # 2. Telefones no texto e links tel: / wa.me
        tels_encontrados = set(re.findall(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}", texto))
        if soup:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                if "wa.me/" in href or "whatsapp.com" in href or "api.whatsapp.com" in href:
                    nums = re.findall(r'\d{10,13}', href)
                    if nums:
                        tels_encontrados.add(nums[0])
                        lead["WhatsApp"] = nums[0]
                elif href.lower().startswith('tel:'):
                    clean_tel = re.sub(r'\D', '', href)
                    if len(clean_tel) in (10, 11, 12, 13):
                        tels_encontrados.add(clean_tel)

        if tels_encontrados:
            if "Telefones_Site" not in lead or not isinstance(lead["Telefones_Site"], list):
                lead["Telefones_Site"] = []
            lead["Telefones_Site"].extend(list(tels_encontrados))
            lead["Telefones_Site"] = list(set(lead["Telefones_Site"]))

        # 3. Redes sociais encontradas no site
        if soup:
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                if "instagram.com/" in href and not any(x in href for x in ('/p/', '/explore/', '/reel/')):
                    if not lead.get("Instagram"):
                        lead["Instagram"] = href
                        self.stats["redes_sociais"] += 1
                elif "facebook.com/" in href and not any(x in href for x in ('/sharer', '/share.php')):
                    if not lead.get("Facebook"):
                        lead["Facebook"] = href
                        self.stats["redes_sociais"] += 1
                elif "linkedin.com/company/" in href or "linkedin.com/in/" in href:
                    if not lead.get("LinkedIn"):
                        lead["LinkedIn"] = href
                        self.stats["redes_sociais"] += 1

        # 4. CNPJ no texto
        cnpjs = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
        if cnpjs and not lead.get("CNPJ_Site"):
            lead["CNPJ_Site"] = cnpjs[0]
            if not lead.get("CNPJ"):
                lead["CNPJ"] = cnpjs[0]
            self.stats["cnpjs_encontrados"] += 1

        # 5. CEP no texto
        ceps = re.findall(r"\b\d{5}-\d{3}\b", texto)
        if ceps and not lead.get("Endereco Fiscal"):
            lead["Endereco Fiscal"] = f"CEP do Site: {ceps[0]}"

    def processar_url(self, url: str, lead: dict, profundidade: int = 0) -> None:
        """Crawl institucional: página inicial + páginas de contato/sobre se existirem."""
        if profundidade > 1 or not url:
            return

        dominios_sociais = ['instagram.com', 'facebook.com', 'linkedin.com']

        # 1. WhatsApp direto na URL
        if "wa.me/" in url or "whatsapp.com" in url or "api.whatsapp.com" in url:
            nums = re.findall(r'\d{10,13}', url)
            if nums:
                if "Telefones_Site" not in lead or not isinstance(lead["Telefones_Site"], list):
                    lead["Telefones_Site"] = []
                lead["Telefones_Site"].append(nums[0])
                lead["WhatsApp"] = nums[0]
                if self.callback:
                    self.callback(f"   WhatsApp direto capturado: {nums[0]}")
            return

        # 2. Rede Social -> DDGS para ler bio
        if any(d in url for d in dominios_sociais):
            if "instagram.com" in url and not lead.get("Instagram"):
                lead["Instagram"] = url
            elif "facebook.com" in url and not lead.get("Facebook"):
                lead["Facebook"] = url
            elif "linkedin.com" in url and not lead.get("LinkedIn"):
                lead["LinkedIn"] = url

            if self.callback:
                self.callback(f"   Rede Social detectada ({url[:30]}...). Lendo bio via DDGS...")
            try:
                if DDGS:
                    query = f'"{url}"'
                    with DDGS() as ddgs:
                        resultados = list(ddgs.text(query, max_results=3))
                        if resultados:
                            texto = " ".join([r.get('body', '') + " " + r.get('title', '') for r in resultados])
                            self.extrair_contatos_html(None, texto, url, lead)
                            links_bio = re.findall(r"(https?://[^\s\"'>]+)", texto)
                            for link in links_bio:
                                if not any(d in link for d in dominios_sociais):
                                    if self.callback:
                                        self.callback(f"   Link da bio encontrado: {link}")
                                    lead["Site"] = link
                                    lead["Site_Extraido_Bio"] = link
                                    self.processar_url(link, lead, profundidade + 1)
                                    break
            except Exception as e:
                logger.debug(f"Erro DDGS para rede social {url}: {e}")
            return

        # 3. Site Institucional Normal
        try:
            url_alvo = url if url.startswith("http") else "http://" + url
            resp = self.get_session().get(url_alvo, timeout=10, verify=False)
            if resp.status_code < 400:
                self.stats["sites_visitados"] += 1
                soup = BeautifulSoup(resp.text, 'html.parser')
                texto = soup.get_text(" ", strip=True)
                self.extrair_contatos_html(soup, texto, url_alvo, lead)

                # Busca links de páginas de contato internas (apenas na home, profundidade == 0)
                if profundidade == 0:
                    links_contato = []
                    termos_contato = ('contato', 'fale-conosco', 'faleconosco', 'sobre', 'quem-somos', 'atendimento')
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href'].strip()
                        href_lower = href.lower()
                        if any(tc in href_lower for tc in termos_contato) and not href.startswith('#') and not href.startswith('mailto:'):
                            link_completo = urllib.parse.urljoin(url_alvo, href)
                            if link_completo != url_alvo and link_completo not in links_contato:
                                links_contato.append(link_completo)

                    # Crawla até 2 páginas de contato internas
                    for sub_url in links_contato[:2]:
                        try:
                            if self.callback:
                                self.callback(f"   Vasculhando página interna: {sub_url.split('/')[-1][:25]}...")
                            resp_sub = self.get_session().get(sub_url, timeout=8, verify=False)
                            if resp_sub.status_code < 400:
                                soup_sub = BeautifulSoup(resp_sub.text, 'html.parser')
                                self.extrair_contatos_html(soup_sub, soup_sub.get_text(" ", strip=True), sub_url, lead)
                        except Exception as e:
                            logger.debug(f"Erro ao ler sub-url {sub_url}: {e}")

                if "Emails_Site" not in lead or not lead["Emails_Site"]:
                    emails_inferred = self.gerar_fallback(url_alvo)
                    if emails_inferred:
                        lead["Emails_Inferidos"] = emails_inferred
            else:
                if profundidade == 0:
                    lead["Site"] = ""
        except requests.exceptions.RequestException as e:
            logger.debug(f"Erro de conexão com {url}: {e}")
            if profundidade == 0:
                lead["Site"] = ""
        except Exception as e:
            logger.warning(f"Erro inesperado ao processar {url}: {e}", exc_info=True)

    def minerar_buscas_navegador(self, empresa: str, cidade: str, lead: dict) -> None:
        """Mineração ativa em mecanismos de busca (DuckDuckGo) por contatos e redes sociais."""
        if not DDGS or not empresa:
            return

        cidade_limpa = re.sub(r'[^\w\s]', '', cidade).strip()[:30]

        # 1. Busca Redes Sociais se ainda não tiver
        if not lead.get("Instagram") or not lead.get("Facebook"):
            try:
                time.sleep(random.uniform(1.0, 2.0))
                query_social = f'"{empresa}" {cidade_limpa} site:instagram.com OR site:facebook.com OR site:linkedin.com'
                with DDGS() as ddgs:
                    for res in ddgs.text(query_social, max_results=4):
                        href = res.get('href', '')
                        if 'instagram.com/' in href and not lead.get("Instagram"):
                            lead["Instagram"] = href
                            self.stats["redes_sociais"] += 1
                        elif 'facebook.com/' in href and not lead.get("Facebook"):
                            lead["Facebook"] = href
                            self.stats["redes_sociais"] += 1
                        elif 'linkedin.com/' in href and not lead.get("LinkedIn"):
                            lead["LinkedIn"] = href
                            self.stats["redes_sociais"] += 1
            except Exception as e:
                logger.debug(f"Erro DDGS redes sociais para {empresa}: {e}")

        # 2. Busca snippets por WhatsApp e telefones se o lead ainda não tem telefone
        if not lead.get("Telefone") and not lead.get("Telefones_Site"):
            try:
                time.sleep(random.uniform(1.0, 2.0))
                query_contato = f'"{empresa}" {cidade_limpa} whatsapp OR telefone OR contato'
                with DDGS() as ddgs:
                    resultados = list(ddgs.text(query_contato, max_results=4))
                    if resultados:
                        texto_busca = " ".join([r.get('body', '') + " " + r.get('title', '') for r in resultados])
                        self.extrair_contatos_html(None, texto_busca, "", lead)
                        # Verifica se algum resultado é o site oficial
                        if not lead.get("Site"):
                            for r in resultados:
                                h = r.get('href', '')
                                if h.startswith("http") and not any(d in h for d in ('instagram', 'facebook', 'linkedin', 'guiamais', 'apontador')):
                                    lead["Site"] = h
                                    break
            except Exception as e:
                logger.debug(f"Erro DDGS contato para {empresa}: {e}")

    def run(self) -> None:
        if self.callback:
            self.callback(f"C-3PO-{self.id} Online (OSINT Multi-Fonte + Deep Crawling).")

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

                # Herda redes sociais já detectadas pelo Maps
                if lead.get("Instagram_Maps") and not lead.get("Instagram"):
                    lead["Instagram"] = lead["Instagram_Maps"]
                if lead.get("Facebook_Maps") and not lead.get("Facebook"):
                    lead["Facebook"] = lead["Facebook_Maps"]
                if lead.get("LinkedIn_Maps") and not lead.get("LinkedIn"):
                    lead["LinkedIn"] = lead["LinkedIn_Maps"]

                if self.callback:
                    self.callback(f"C-3PO-{self.id}: Investigando '{empresa}'...")

                # Mineração ativa nos navegadores se faltar site, telefone ou rede social
                if not url or not lead.get("Telefone") or not lead.get("Instagram"):
                    self.minerar_buscas_navegador(empresa, cidade, lead)
                    if not url and lead.get("Site"):
                        url = lead.get("Site")

                # Se temos site (ou rede social como site), faz deep crawl
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
            f"RELATÓRIO C-3PO-{self.id}:\n"
            f"   - Processados: {self.stats['lidos']}\n"
            f"   - Sites Visitados: {self.stats['sites_visitados']}\n"
            f"   - E-mails Encontrados: {self.stats['emails_encontrados']}\n"
            f"   - Redes Sociais Identificadas: {self.stats['redes_sociais']}\n"
            f"   - Erros: {self.stats['erros']}"
        )
        logger.info(relatorio)
        if self.callback:
            self.callback(relatorio)

    def parar(self) -> None:
        self.rodando = False
