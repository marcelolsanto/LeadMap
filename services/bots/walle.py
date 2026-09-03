"""
services/bots/walle.py
Wall-E: Higienizador e validador final de leads.
Suporta estado por sessao e logging estruturado.
"""
import threading
import queue
import re
from utils.logger import get_logger

logger = get_logger(__name__)


class WorkerWallE(threading.Thread):
    def __init__(self, callback_log=None, id_robo: int = 1,
                 fila_api=None, resultados_finais=None, lock_ativos=None, ativos_agora=None):
        """
        Args:
            callback_log: Funcao de callback para logs na UI
            id_robo: Identificador numerico do worker
            fila_api: Fila de entrada (PipelineState.fila_api)
            resultados_finais: ResultadosThread de saida (PipelineState.resultados_finais)
            lock_ativos: Lock para ativos_agora
            ativos_agora: Dict de contagem de workers ativos
        """
        super().__init__(daemon=True)
        self.callback = callback_log
        self.id = id_robo
        self.rodando = True
        self.stats = {
            "lidos": 0,
            "emails_validos": 0,
            "tels_formatados": 0,
            "enderecos_corrigidos": 0
        }

        if fila_api is not None:
            self._fila_api = fila_api
            self._resultados_finais = resultados_finais
            self._lock_ativos = lock_ativos
            self._ativos_agora = ativos_agora
        else:
            from services.state import fila_api as _fa, resultados_finais as _rf, lock_ativos as _la, ativos_agora as _aa
            self._fila_api = _fa
            self._resultados_finais = _rf
            self._lock_ativos = _la
            self._ativos_agora = _aa

    def formatar_telefone(self, fone) -> str | None:
        """Normaliza telefone para formato +55XXXXXXXXXXX."""
        if not fone:
            return None
        nums = re.sub(r'\D', '', str(fone))
        if not nums:
            return None
        if nums.startswith('0'):
            nums = nums[1:]
        if not nums.startswith('55') and len(nums) in (10, 11):
            nums = f"55{nums}"
        if len(nums) in (12, 13) and nums.startswith('55'):
            return f"+{nums}"
        return None

    def validar_email(self, email) -> str | None:
        """Valida e sanitiza a sintaxe de um endereço de e-mail."""
        if not email or not isinstance(email, str):
            return None
        try:
            from services.email_validator import validar_sintaxe_email
            return validar_sintaxe_email(email)
        except Exception:
            return None

    def validar_email_com_ping(self, email) -> tuple[str | None, str]:
        """Valida email com checagem de servidor de correio DNS/MX e ping."""
        if not email or not isinstance(email, str):
            return None, ""
        try:
            from services.email_validator import validar_email_completo
            email_limpo, valido, status = validar_email_completo(email, verificar_ping=True)
            if valido and email_limpo:
                return email_limpo, status
            # Se a checagem de DNS falhar (ex: domínio de teste/intranet), verifica sintaxe
            sintaxe = self.validar_email(email)
            if sintaxe:
                return sintaxe, "Sintaxe Válida"
        except Exception as e:
            logger.debug(f"Erro na validação de e-mail com ping {email}: {e}")
            sintaxe = self.validar_email(email)
            if sintaxe:
                return sintaxe, "Sintaxe Válida"
        return None, ""

    def eleger_melhor_contato(self, lead: dict) -> dict:
        """Seleciona os melhores dados de cada campo usando cascata de prioridade."""
        import urllib.parse

        # A. ENDERECO HIBRIDO
        end_fiscal = lead.get("Endereco Fiscal")
        end_maps = lead.get("Endereco") or lead.get("Endereço")

        if end_fiscal and len(str(end_fiscal).strip()) > 5:
            melhor_endereco = str(end_fiscal).strip()
        else:
            melhor_endereco = str(end_maps).strip() if end_maps else None

        if melhor_endereco:
            lead["Endereço"] = melhor_endereco.title()
            self.stats["enderecos_corrigidos"] += 1
        else:
            lead["Endereço"] = None

        # Link do ponto exato no Google Maps
        if not lead.get("Google_Maps_Url"):
            nome_emp = lead.get("Empresa", "")
            local = lead.get("Endereço", "") or ""
            termo_mapa = urllib.parse.quote_plus(f"{nome_emp}, {local}".strip(", "))
            lead["Google_Maps_Url"] = f"https://www.google.com/maps/search/?api=1&query={termo_mapa}"

        # B. SITE E REDES SOCIAIS
        site_bruto = lead.get("Site", "")
        site_bio = lead.get("Site_Extraido_Bio", "")
        insta = lead.get("Instagram") or lead.get("Instagram_Maps", "")
        face = lead.get("Facebook") or lead.get("Facebook_Maps", "")
        linkin = lead.get("LinkedIn") or lead.get("LinkedIn_Maps", "")

        lead["Instagram"] = insta if insta else ""
        lead["Facebook"] = face if face else ""
        lead["LinkedIn"] = linkin if linkin else ""

        # Cascata: Site Bio > Site Maps/Crawl > Insta > Face > LinkedIn
        link_final = site_bio if site_bio else site_bruto
        if not link_final:
            link_final = insta if insta else (face if face else linkin)

        if not link_final or link_final == "Nao possui / Quebrado":
            lead["Site"] = "Nao possui"
            lead["Tipo_Link"] = "Nenhum"
        else:
            if not str(link_final).startswith("http"):
                link_final = "https://" + str(link_final)
            lead["Site"] = link_final

            if "instagram.com" in link_final:
                lead["Tipo_Link"] = "Instagram"
            elif "facebook.com" in link_final or "fb.com" in link_final:
                lead["Tipo_Link"] = "Facebook"
            elif "linkedin.com" in link_final:
                lead["Tipo_Link"] = "LinkedIn"
            else:
                lead["Tipo_Link"] = "Site Oficial"

        # C. EMAILS COM PING DE CONFIRMAÇÃO DE SERVIDOR
        melhor_email = None
        status_email = ""
        candidatos_certeza = []

        if lead.get("Email_Fiscal"):
            candidatos_certeza.append(lead.get("Email_Fiscal"))
        site_emails = lead.get("Emails_Site")
        if isinstance(site_emails, list):
            candidatos_certeza.extend(site_emails)
        elif isinstance(site_emails, str):
            candidatos_certeza.append(site_emails)
        if lead.get("Site") and "@" in str(lead.get("Site", "")):
            candidatos_certeza.append(lead.get("Site"))

        for cand in candidatos_certeza:
            validado, st_msg = self.validar_email_com_ping(cand)
            if validado:
                melhor_email = validado
                status_email = st_msg
                if self.callback:
                    self.callback(f"   E-mail validado ({st_msg}): {validado}")
                break

        if not melhor_email:
            inferidos = lead.get("Emails_Inferidos", [])
            for cand in inferidos:
                validado, st_msg = self.validar_email_com_ping(cand)
                if validado:
                    melhor_email = validado
                    status_email = st_msg
                    if self.callback:
                        self.callback(f"   E-mail inferido aprovado ({st_msg}): {validado}")
                    break

        if melhor_email:
            self.stats["emails_validos"] += 1

        lead["Email"] = melhor_email
        lead["Melhor_Email"] = melhor_email
        lead["Email_Valido"] = status_email if melhor_email else "Não encontrado"

        # D. TELEFONES E WHATSAPP
        candidatos_fone = []
        if lead.get("WhatsApp"):
            candidatos_fone.append(lead.get("WhatsApp"))
        if lead.get("Telefone_Fiscal"):
            candidatos_fone.append(lead.get("Telefone_Fiscal"))
        if lead.get("Telefone"):
            candidatos_fone.append(lead.get("Telefone"))
        site_fones = lead.get("Telefones_Site")
        if isinstance(site_fones, list):
            candidatos_fone.extend(site_fones)
        elif isinstance(site_fones, str):
            candidatos_fone.append(site_fones)

        melhor_fone = None
        for cand in candidatos_fone:
            fmt = self.formatar_telefone(cand)
            if fmt:
                melhor_fone = fmt
                break

        if melhor_fone:
            self.stats["tels_formatados"] += 1
            nums_puros = re.sub(r'\D', '', melhor_fone)
            lead["WhatsApp_Url"] = f"https://wa.me/{nums_puros}?text=Ol%C3%A1%2C+vi+sua+empresa+no+Google+Maps"
        else:
            lead["WhatsApp_Url"] = ""

        lead["Telefone"] = melhor_fone
        lead["Melhor_Telefone"] = melhor_fone

        return lead

    def run(self) -> None:
        if self.callback:
            self.callback(f"Wall-E-{self.id}: Ativado (Validacao Regex + Hibrido).")

        while self.rodando or not self._fila_api.empty():
            lead = None
            try:
                lead = self._fila_api.get(timeout=1)
                with self._lock_ativos:
                    self._ativos_agora["WALLE"] += 1
                self.stats["lidos"] += 1

                lead_v2 = self.eleger_melhor_contato(lead)
                self._resultados_finais.append(lead_v2)  # thread-safe via ResultadosThread

            except queue.Empty:
                continue
            except Exception as e:
                self.stats["erros"] = self.stats.get("erros", 0) + 1
                logger.error(f"Wall-E-{self.id} erro inesperado: {e}", exc_info=True)
            finally:
                if lead is not None:
                    self._fila_api.task_done()
                    with self._lock_ativos:
                        self._ativos_agora["WALLE"] -= 1

        relatorio = (
            f"RELATORIO WALL-E-{self.id}:\n"
            f"   - Processados: {self.stats['lidos']}\n"
            f"   - E-mails Validos: {self.stats['emails_validos']}\n"
            f"   - Telefones Formatados: {self.stats['tels_formatados']}\n"
            f"   - Enderecos Hibridos: {self.stats['enderecos_corrigidos']}"
        )
        logger.info(relatorio)
        if self.callback:
            self.callback(relatorio)

    def parar(self) -> None:
        self.rodando = False
