"""
services/bots/r2d2.py
R2-D2: Auditor de CNPJ via DuckDuckGo + BrasilAPI.
Suporta estado por sessao e logging estruturado.
"""
import threading
import queue
import re
import time
import random
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
from services import enrichment_service
from utils.logger import get_logger

logger = get_logger(__name__)
def _validar_digitos_cnpj(cnpj: str) -> bool:
    """Valida os digitos verificadores do CNPJ. Retorna True se valido."""
    nums = [int(c) for c in cnpj if c.isdigit()]
    if len(nums) != 14:
        return False
    # Todos iguais sao invalidos
    if len(set(nums)) == 1:
        return False
    # Calculo do primeiro digito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(nums[i] * pesos1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if nums[12] != d1:
        return False
    # Calculo do segundo digito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(nums[i] * pesos2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    return nums[13] == d2



class WorkerR2D2(threading.Thread):
    def __init__(self, callback_log=None, id_robo: int = 1,
                 fila_web=None, fila_api=None, lock_ativos=None, ativos_agora=None):
        """
        Args:
            callback_log: Funcao de callback para logs na UI
            id_robo: Identificador numerico do worker
            fila_web: Fila de entrada (PipelineState.fila_web)
            fila_api: Fila de saida (PipelineState.fila_api)
            lock_ativos: Lock para ativos_agora
            ativos_agora: Dict de contagem de workers ativos
        """
        super().__init__(daemon=True)
        self.callback = callback_log
        self.id = id_robo
        self.rodando = True
        self.stats = {"lidos": 0, "cnpjs_google": 0, "enriquecidos": 0, "erros": 0}

        if fila_web is not None:
            self._fila_web = fila_web
            self._fila_api = fila_api
            self._lock_ativos = lock_ativos
            self._ativos_agora = ativos_agora
        else:
            from services.state import fila_web as _fw, fila_api as _fa, lock_ativos as _la, ativos_agora as _aa
            self._fila_web = _fw
            self._fila_api = _fa
            self._lock_ativos = _la
            self._ativos_agora = _aa

    def investigar_cnpj(self, nome_empresa: str, cidade: str = "", site: str = "") -> str | None:
        """Busca CNPJ via DuckDuckGo com múltiplas estratégias (Nome, Cidade, Domínio)."""
        termo_limpo = re.sub(r'[^\w\s]', '', nome_empresa.split('-')[0])
        termo_limpo = termo_limpo.replace(" LTDA", "").replace(" SA", "").replace(" ME", "").replace(" EPP", "").strip()
        if len(termo_limpo) < 3:
            return None

        padrao = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'

        queries = [f'"{termo_limpo}" CNPJ']
        if cidade:
            cidade_limpa = re.sub(r'[^\w\s]', '', cidade).strip()[:25]
            if cidade_limpa:
                queries.append(f'"{termo_limpo}" {cidade_limpa} CNPJ')
        if site and "http" in site and not any(d in site for d in ('instagram', 'facebook', 'linkedin')):
            dominio = site.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
            if dominio:
                queries.append(f'"{dominio}" CNPJ')

        try:
            if DDGS:
                with DDGS() as ddgs:
                    for query in queries:
                        resultados = list(ddgs.text(query, max_results=3))
                        for res in resultados:
                            texto_resultado = res.get('body', '') + " " + res.get('title', '')
                            matches = re.findall(padrao, texto_resultado)
                            for match in matches:
                                cnpj_limpo = re.sub(r'\D', '', match).zfill(14)
                                if len(cnpj_limpo) == 14 and _validar_digitos_cnpj(cnpj_limpo):
                                    return match
                        time.sleep(0.4)
        except Exception as e:
            logger.debug(f"Erro DDGS ao buscar CNPJ de '{nome_empresa}': {e}")

        return None

    def run(self) -> None:
        if self.callback:
            self.callback(f"R2-D2-{self.id} Online (Blindado via DDGS + BrasilAPI).")

        while self.rodando or not self._fila_web.empty():
            lead = None
            try:
                lead = self._fila_web.get(timeout=1)
                with self._lock_ativos:
                    self._ativos_agora["R2D2"] += 1
                self.stats["lidos"] += 1

                cnpj = lead.get("CNPJ")
                nome_empresa = lead.get("Empresa")
                precisa_auditar = False

                if cnpj:
                    precisa_auditar = True
                elif nome_empresa:
                    if self.callback:
                        self.callback(f"R2-D2-{self.id}: Investigando '{nome_empresa}'...")
                    cnpj_achado = self.investigar_cnpj(
                        nome_empresa,
                        cidade=lead.get("Endereco", lead.get("Endereço", "")),
                        site=lead.get("Site", "")
                    )
                    if cnpj_achado:
                        cnpj = cnpj_achado
                        lead["CNPJ"] = cnpj
                        self.stats["cnpjs_google"] += 1
                        if self.callback:
                            self.callback(f"   Achei CNPJ: {cnpj}")
                        precisa_auditar = True
                    else:
                        if self.callback:
                            self.callback(f"   CNPJ nao encontrado.")

                if precisa_auditar and cnpj:
                    cnpj_limpo = re.sub(r'[^0-9]', '', str(cnpj)).zfill(14)
                    if len(cnpj_limpo) == 14 and _validar_digitos_cnpj(cnpj_limpo):
                        dados = enrichment_service.consultar_empresa(cnpj_limpo)
                        if dados:
                            self.stats["enriquecidos"] += 1
                            lead.update({
                                "Razao Social": dados.get("razao_social"),
                                "Email_Fiscal": dados.get("email_fiscal"),
                                "Telefone_Fiscal": dados.get("telefone_fiscal"),
                                "Endereco Fiscal": dados.get("endereco_fiscal"),
                                "Situacao": dados.get("situacao")
                            })
                            if dados.get("email_fiscal") and self.callback:
                                self.callback(f"   E-mail Fiscal encontrado!")
                        else:
                            time.sleep(0.5)

            except queue.Empty:
                continue
            except Exception as e:
                self.stats["erros"] += 1
                logger.error(f"R2-D2-{self.id} erro inesperado: {e}", exc_info=True)
            finally:
                if lead is not None:
                    self._fila_api.put(lead)
                    self._fila_web.task_done()
                    with self._lock_ativos:
                        self._ativos_agora["R2D2"] -= 1

        relatorio = (
            f"RELATORIO R2-D2-{self.id}:\n"
            f"   - Processados: {self.stats['lidos']}\n"
            f"   - CNPJs via DDGS: {self.stats['cnpjs_google']}\n"
            f"   - Enriquecidos via API: {self.stats['enriquecidos']}\n"
            f"   - Erros: {self.stats['erros']}"
        )
        logger.info(relatorio)
        if self.callback:
            self.callback(relatorio)

    def parar(self) -> None:
        self.rodando = False

