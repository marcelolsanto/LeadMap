import re


def limpar_endereco(texto_completo, nome, telefone):
    # 1. Remove Nome e Telefone conhecidos
    texto = texto_completo.replace(nome, "").replace(telefone, "")

    # 2. Normaliza quebras de linha e pontos de separação
    texto = texto.replace("\n", " ").replace("·", " ").replace("⋅", " ").replace("•", " ").strip()

    # 3. Regex Poderoso para remover "lixo" do Google Maps
    # Adicionamos: "Aberto", "Fecha às", horários, parênteses de avaliação (120), Rotas, ícones
    padroes_remocao = [
        r"Anúncio",
        r"Patrocinado",
        r"Aberto(\s+agora)?",
        r"Fecha(\s+(às|as))?\s+\d{1,2}:\d{2}",
        r"Fechado",
        r"copiar endereço",
        r"Avaliação",
        r"comentários?",
        r"Opções de serviço:.*",
        r"Rotas(\s*↗)?",
        r"\b\d+[\.,]\d+\b\s*(\(\d+\))?",  # Pega nota ex: "4.8 (120)" ou "3,0"
        r"Compras na loja",
        r"Entrega",
        r"[\ue000-\uf8ff]",  # Caracteres unicode especiais de ícones (ex: )
    ]

    regex_final = "|".join(padroes_remocao)
    texto = re.sub(regex_final, "", texto, flags=re.IGNORECASE)

    # 4. Limpeza final de espaços duplos e vírgulas soltas
    texto = re.sub(r'\s+', ' ', texto).strip()
    texto = texto.strip(", -")  # Remove vírgulas ou traços no começo/fim

    return texto[:120]
