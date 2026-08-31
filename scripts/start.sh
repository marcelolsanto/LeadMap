#!/bin/bash
set -e

echo "Iniciando LeadMap Pro..."

# Inicia Streamlit (o webhook server roda automaticamente na thread daemon via app.py)
exec streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
