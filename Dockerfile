# Imagem base oficial do Playwright com Python e Chromium pré-instalados
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Diretório de trabalho
WORKDIR /app

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    LOG_FILE=/app/logs/erros_robo.log

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python com cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Garante browsers do Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copia código do projeto
COPY . .

# Remove pasta fantasma que Docker pode ter criado no lugar do arquivo de log
# e garante existência dos diretórios de persistência
RUN rm -rf /app/erros_robo.log && \
    mkdir -p data/backups_usuarios data/usuarios perfil_chrome logs

# Expõe portas: 8501 (Streamlit UI) e 8502 (Stripe Webhook Server)
EXPOSE 8501 8502

# Healthcheck do container
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando de entrada
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
