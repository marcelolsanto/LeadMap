import pytest
import sys
import time
import os


def print_header(text):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def run_quality_assurance():
    print_header("🛡️ INICIANDO PROTOCOLO DE QA - LEADMAP PRO 🛡️")
    time.sleep(1)

    print("🔍 1. Verificando Estrutura de Arquivos...")
    # Lista de arquivos que DEVEM existir para o software funcionar
    essenciais = ["app.py", "main.py", ".env", "requirements.txt", "modules/stealth.py"]
    missing = []
    for f in essenciais:
        if os.path.exists(f):
            print(f"   ✅ Encontrado: {f}")
        else:
            print(f"   ❌ FALTANDO: {f}")
            missing.append(f)

    if missing:
        print("\n🚫 ABORTAR: Arquivos essenciais faltando.")
        return

    print("\n🔍 2. Executando Bateria de Testes Automatizados (Pytest)...")
    time.sleep(1)

    # Roda o Pytest e captura o resultado
    exit_code = pytest.main(["-v", "tests/"])

    print_header("RELATÓRIO FINAL")

    if exit_code == 0:
        print("✅ SUCESSO TOTAL!")
        print("   Todos os sistemas estão operacionais.")
        print("   O código está seguro, limpo e funcional.")
    else:
        print("❌ FALHA NOS TESTES")
        print("   Corrija os erros listados acima antes de prosseguir.")


if __name__ == "__main__":
    run_quality_assurance()
