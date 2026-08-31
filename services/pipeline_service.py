# services/pipeline_service.py
# Re-exporta as classes e o gerenciamento de estado do pipeline
from services.state import (
    session_manager,
    PipelineState,
    ResultadosThread,
    fila_raw,
    fila_web,
    fila_api,
    resultados_finais,
    ativos_agora,
    lock_ativos,
    estatisticas,
    status_pipeline
)

# Re-exporta as classes dos robos
from services.bots.c3po import WorkerC3PO
from services.bots.r2d2 import WorkerR2D2
from services.bots.walle import WorkerWallE
