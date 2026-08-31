import random

class ProxyManager:
    def __init__(self):
        # Mantenha a lista vazia para rodar com seu IP local inicialmente
        self.proxies = []

    def get_proxy(self):
        # AQUI ESTAVA O ERRO: Precisamos checar se a lista tem itens PRIMEIRO
        if not self.proxies:
            print("ℹ️ Modo Local: Nenhum proxy configurado. Usando conexão direta.")
            return None  # O Playwright entende None como "sem proxy"

        # Só tenta escolher se a lista NÃO estiver vazia
        proxy_string = random.choice(self.proxies)
        return {"server": proxy_string}
