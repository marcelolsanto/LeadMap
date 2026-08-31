# salve como captcha_solver.py
from twocaptcha import TwoCaptcha
import time
import os

class CaptchaSolver:
    def __init__(self, api_key):
        api_key = os.getenv("API_KEY_2CAPTCHA")
        if not api_key:
            raise ValueError("API Key do 2Captcha não encontrada no arquivo .env")
        self.solver = TwoCaptcha(api_key)

    def resolver_recaptcha_v2(self, site_key, url_pagina):
        """
        Envia o desafio para a API e retorna o token de solução.
        """
        print("--- 🧩 CAPTCHA detectado! Enviando para resolução... ---")
        try:
            # Envia para a 2Captcha
            resultado = self.solver.recaptcha(
                sitekey=site_key,
                url=url_pagina
            )
            print("--- ✅ CAPTCHA resolvido com sucesso! ---")
            return resultado['code']  # Este é o token mágico

        except Exception as e:
            print(f"--- ❌ Falha ao resolver CAPTCHA: {e} ---")
            return None
