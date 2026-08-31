import threading
from services import state
from services import enrichment_service
# Conexão 1: Ele precisa buscar o "cérebro" na pasta scraper
from scraper.core import GoogleMapsScraper


class WorkerBB8(threading.Thread):
    def __init__(self, scraper_instance, termo, fila_saida):
        super().__init__()
        self.scraper = scraper_instance
        self.termo = termo
        self.fila_saida = fila_saida
        self.nome = "BB-8"

    def run(self):
        state.ESTEIRA_LIGADA = True
        print(f"[{self.nome}] 🟢 Iniciando varredura...")

        try:
            # O BB-8 usa o cérebro (Scraper) para trabalhar
            self.scraper.start()
        except Exception as e:
            print(f"[{self.nome}] ❌ Erro: {e}")

        # Avisa que terminou
        self.fila_saida.put(None)
