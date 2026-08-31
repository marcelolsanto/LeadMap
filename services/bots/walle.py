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
        """Valida e sanitiza um endereco de email."""
        if not email or not isinstance(email, str):
            return None
        email = email.lower().strip()
        bloqueados = [
            'sentry', 'wixpress', 'noreply', 'nao-responda',
            'usuario@', 'exemplo.com', 'domain.com', 'email@',
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.js', '.css',
            'hostmaster', 'postmaster', 'webmaster', 'support@wix',
            'instagram.com', 'facebook.com', 'fb.com', 'wa.me', 'whatsapp.com',
            'linktr.ee', 'linkedin.com', 'youtube.com', 'tiktok.com'
        ]
        if any(x in email for x in bloqueados):
            return None
        if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return email
        return None

    def eleger_melhor_contato(self, lead: dict) -> dict:
        """Seleciona os melhores dados de cada campo usando cascata de prioridade."""

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

        # B. SITE E REDES SOCIAIS
        site_bruto = lead.get("Site", "")
        site_bio = lead.get("Site_Extraido_Bio", "")
        insta_maps = lead.get("Instagram_Maps", "")
        face_maps = lead.get("Facebook_Maps", "")
        link_maps = lead.get("LinkedIn_Maps", "")

        # Cascata: Site Bio > Site Maps > Insta > Face > LinkedIn
        link_final = site_bio if site_bio else site_bruto
        if not link_final:
            link_final = insta_maps if insta_maps else (face_maps if face_maps else link_maps)

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

        # C. EMAILS
        melhor_email = None
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
            validado = self.validar_email(cand)
            if validado:
                melhor_email = validado
                if self.callback:
                    self.callback(f"   E-mail aprovado: {validado}")
                break

        if not melhor_email:
            inferidos = lead.get("Emails_Inferidos", [])
            for cand in inferidos:
                validado = self.validar_email(cand)
                if validado:
                    melhor_email = validado
                    if self.callback:
                        self.callback(f"   E-mail inferido aprovado: {validado}")
                    break

        if melhor_email:
            self.stats["emails_validos"] += 1

        lead["Email"] = melhor_email
        lead["Melhor_Email"] = melhor_email

        # D. TELEFONES
        candidatos_fone = []
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
