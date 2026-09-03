import sqlite3
import pandas as pd
from datetime import datetime
import os

from utils.logger import get_logger

logger = get_logger(__name__)

DB_LEADS = "data/leads.db"
DB_LOGS = "data/leadmap_data.db"

if not os.path.exists("data"):
    os.makedirs("data", exist_ok=True)


def _enable_wal(conn: sqlite3.Connection) -> None:
    """Ativa WAL mode para suportar múltiplos writers sem lock."""
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception as e:
        logger.warning(f"Nao foi possivel ativar WAL mode: {e}")


def init_dbs():
    """Inicializa todas as tabelas se nao existirem."""

    # 1. Banco de LEADS
    try:
        conn_leads = sqlite3.connect(DB_LEADS)
        _enable_wal(conn_leads)
        cursor = conn_leads.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa TEXT,
                email TEXT,
                telefone TEXT,
                site TEXT,
                endereco TEXT,
                cnpj TEXT,
                nicho TEXT,
                origem TEXT,
                data_captura TEXT,
                hash_unico TEXT UNIQUE
            )
        """)
        # Indices para buscas rapidas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_nicho ON leads(nicho);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_empresa ON leads(empresa);")
        conn_leads.commit()
        conn_leads.close()
    except Exception as e:
        logger.error(f"Erro ao iniciar DB Leads: {e}", exc_info=True)

    # 2. Banco de LOGS
    try:
        conn_logs = sqlite3.connect(DB_LOGS)
        _enable_wal(conn_logs)
        cursor = conn_logs.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                email TEXT,
                acao TEXT,
                detalhes TEXT
            )
        """)
        conn_logs.commit()
        conn_logs.close()
    except Exception as e:
        logger.error(f"Erro ao iniciar DB Logs: {e}", exc_info=True)

    # 3. Tabela USUARIOS (sem credenciais OAuth)
    try:
        conn = sqlite3.connect(DB_LOGS)
        _enable_wal(conn)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                email TEXT PRIMARY KEY,
                nome TEXT,
                foto TEXT,
                ultimo_login TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao iniciar Tabela Usuarios: {e}", exc_info=True)

    # 4. Tabela ASSINATURAS (Stripe Webhook)
    try:
        conn = sqlite3.connect(DB_LOGS)
        _enable_wal(conn)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assinaturas (
                email TEXT PRIMARY KEY,
                status TEXT,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                valido_ate TEXT,
                atualizado_em TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao iniciar Tabela Assinaturas: {e}", exc_info=True)


# --- LEADS ---

def salvar_lote_leads(lista_leads: list, nicho_atual: str) -> int:
    """Salva leads ignorando duplicatas. Retorna quantidade de novos leads."""
    if not lista_leads:
        return 0

    conn = sqlite3.connect(DB_LEADS)
    _enable_wal(conn)
    cursor = conn.cursor()
    count_novos = 0
    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for lead in lista_leads:
        try:
            chave = f"{lead.get('Empresa')}-{lead.get('Telefone')}"
            cursor.execute("""
                INSERT OR IGNORE INTO leads
                (empresa, email, telefone, site, endereco, cnpj, nicho, origem, data_captura, hash_unico)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.get("Empresa"),
                lead.get("Email") or lead.get("Melhor_Email"),
                lead.get("Telefone") or lead.get("Melhor_Telefone"),
                lead.get("Site"),
                lead.get("Endereco") or lead.get("Endereço"),
                lead.get("CNPJ"),
                nicho_atual,
                "LeadMap Pro",
                data_hoje,
                chave
            ))
            if cursor.rowcount > 0:
                count_novos += 1
        except Exception as e:
            logger.warning(f"Erro ao salvar lead '{lead.get('Empresa')}': {e}")

    conn.commit()
    conn.close()
    return count_novos


# --- LOGS ---

def registrar_log(email: str, acao: str, detalhes: str) -> None:
    """Registra ação do usuário no banco."""
    try:
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        conn = sqlite3.connect(DB_LOGS)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs_usuarios (data_hora, email, acao, detalhes)
            VALUES (?, ?, ?, ?)
        """, (data_hora, email, acao, str(detalhes)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao salvar log: {e}", exc_info=True)


# --- USUARIOS ---

def salvar_usuario_db(user_info: dict) -> bool:
    """
    Salva ou atualiza dados do usuário.
    NOTA DE SEGURANÇA: credenciais OAuth NAO são salvas no banco.
    Elas residem apenas na st.session_state (memória volátil).
    """
    try:
        conn = sqlite3.connect(DB_LOGS)
        cursor = conn.cursor()
        data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO usuarios (email, nome, foto, ultimo_login)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                nome=excluded.nome,
                foto=excluded.foto,
                ultimo_login=excluded.ultimo_login
        """, (
            user_info.get("email"),
            user_info.get("name"),
            user_info.get("picture"),
            data_hoje
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar usuario no DB: {e}", exc_info=True)
        return False


# --- ASSINATURAS (Stripe Webhook) ---

def salvar_assinatura(email: str, status: str, customer_id: str,
                      subscription_id: str, valido_ate: str) -> bool:
    """Cria ou atualiza o registro de assinatura de um usuário."""
    try:
        conn = sqlite3.connect(DB_LOGS)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO assinaturas
                (email, status, stripe_customer_id, stripe_subscription_id, valido_ate, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                status=excluded.status,
                stripe_customer_id=excluded.stripe_customer_id,
                stripe_subscription_id=excluded.stripe_subscription_id,
                valido_ate=excluded.valido_ate,
                atualizado_em=excluded.atualizado_em
        """, (email, status, customer_id, subscription_id, valido_ate, agora))

        conn.commit()
        conn.close()
        logger.info(f"Assinatura atualizada: {email} -> {status}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar assinatura: {e}", exc_info=True)
        return False


def consultar_assinatura(email: str) -> dict | None:
    """Retorna dados de assinatura do usuário ou None se nao existir."""
    try:
        conn = sqlite3.connect(DB_LOGS)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assinaturas WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao consultar assinatura de {email}: {e}", exc_info=True)
        return None


def atualizar_status_assinatura(email: str, novo_status: str) -> bool:
    """Atualiza apenas o status de uma assinatura existente."""
    try:
        conn = sqlite3.connect(DB_LOGS)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE assinaturas SET status=?, atualizado_em=? WHERE email=?",
            (novo_status, agora, email)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status assinatura de {email}: {e}", exc_info=True)
        return False
