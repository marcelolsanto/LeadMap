import pytest
from services import repository


@pytest.fixture(autouse=True)
def setup_test_dbs(monkeypatch, tmp_path):
    test_leads_db = str(tmp_path / "leads.db")
    test_logs_db = str(tmp_path / "leadmap_data.db")

    monkeypatch.setattr(repository, "DB_LEADS", test_leads_db)
    monkeypatch.setattr(repository, "DB_LOGS", test_logs_db)

    repository.init_dbs()


def test_salvar_e_consultar_assinatura():
    sucesso = repository.salvar_assinatura(
        email="cliente@empresa.com",
        status="active",
        customer_id="cus_123",
        subscription_id="sub_456",
        valido_ate="2026-12-31 23:59:59"
    )
    assert sucesso is True

    assinatura = repository.consultar_assinatura("cliente@empresa.com")
    assert assinatura is not None
    assert assinatura["status"] == "active"
    assert assinatura["stripe_customer_id"] == "cus_123"

    # Atualiza status
    atualizado = repository.atualizar_status_assinatura("cliente@empresa.com", "canceled")
    assert atualizado is True

    assinatura_cancelada = repository.consultar_assinatura("cliente@empresa.com")
    assert assinatura_cancelada["status"] == "canceled"


def test_salvar_usuario_sem_credenciais():
    user_info = {
        "id": "12345",
        "email": "user@gmail.com",
        "name": "Usuario Teste",
        "picture": "https://foto.jpg"
    }

    sucesso = repository.salvar_usuario_db(user_info)
    assert sucesso is True


def test_salvar_lote_leads():
    leads = [
        {
            "Empresa": "Padaria A",
            "Telefone": "(11) 91111-1111",
            "Email": "a@padaria.com",
            "Site": "https://padariaa.com",
            "Endereco": "Rua A, 1",
            "CNPJ": "11.111.111/0001-11"
        },
        {
            "Empresa": "Padaria B",
            "Telefone": "(11) 92222-2222",
            "Email": "b@padaria.com",
            "Site": "https://padariab.com",
            "Endereco": "Rua B, 2",
            "CNPJ": "22.222.222/0001-22"
        }
    ]

    novos = repository.salvar_lote_leads(leads, "Padaria")
    assert novos == 2

    # Duplicatas devem ser ignoradas
    duplicados = repository.salvar_lote_leads(leads, "Padaria")
    assert duplicados == 0
