try:
    from playwright_stealth import stealth_sync
    print("\n✅ SUCESSO! A camuflagem Stealth está instalada e pronta.")
except ImportError as e:
    print(f"\n❌ ERRO AINDA PERSISTE: {e}")
    print("Tente rodar: pip install --upgrade playwright-stealth")
