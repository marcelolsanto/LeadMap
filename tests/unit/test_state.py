import threading
from services.state import ResultadosThread, PipelineState, SessionManager


def test_resultados_thread_safe():
    res = ResultadosThread()

    def worker_append(start, count):
        for i in range(count):
            res.append({"id": start + i})

    threads = []
    for t_idx in range(5):
        t = threading.Thread(target=worker_append, args=(t_idx * 100, 100))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(res) == 500
    copy_list = res.copy()
    assert len(copy_list) == 500
    assert isinstance(copy_list, list)

    res.clear()
    assert len(res) == 0


def test_pipeline_state_reset():
    state = PipelineState("test-session-123")
    state.fila_raw.put({"lead": 1})
    state.resultados_finais.append({"lead": 1})
    state.estatisticas["total_bb8"] = 10
    state.status_pipeline["bb8_terminou"] = True

    state.reset()

    assert state.fila_raw.empty()
    assert len(state.resultados_finais) == 0
    assert state.estatisticas["total_bb8"] == 0
    assert state.status_pipeline["bb8_terminou"] is False


def test_session_manager_isolation():
    manager = SessionManager()
    state_a = manager.get_or_create("session-A")
    state_b = manager.get_or_create("session-B")

    state_a.resultados_finais.append({"empresa": "A"})
    assert len(state_a.resultados_finais) == 1
    assert len(state_b.resultados_finais) == 0

    assert manager.active_count() == 2
    manager.destroy("session-A")
    assert manager.active_count() == 1
