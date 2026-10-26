from copy import deepcopy
import importlib

import pytest
from app import app as interface
from app import history_store


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "HISTORY_PATH", str(tmp_path / "consultas.sqlite3")
    )
    return monkeypatch


def resultado():
    return {
        "query": "Quantos itens?",
        "query_id": "q_historico",
        "run_id": "run_historico",
        "answer": "Total de itens: 19",
        "executado": True,
        "estrategia": "consulta_agregada",
        "operacao": "resumir_itens",
        "routes": ["agregada"],
        "filters": {},
        "fontes": ["itens.csv"],
        "campos": ["indicador", "resultado"],
        "registros": [{"indicador": "Total de itens", "resultado": 19}],
    }


def test_consulta_da_interface_e_persistida(ambiente):
    item = resultado()
    ambiente.setattr(
        interface, "executar_pipeline",
        lambda *args, **kwargs: deepcopy(item),
    )
    interface.executar(item["query"], 3, progress=lambda *a, **k: None)
    assert history_store.carregar_consulta("run_historico") == item


def test_reabrir_apos_reload_nao_executa_pipeline(ambiente):
    item = resultado()
    history_store.salvar_consulta(item)
    importlib.reload(history_store)

    def proibido(*args, **kwargs):
        raise AssertionError("Histórico não deve executar o pipeline.")

    ambiente.setattr(interface, "executar_pipeline", proibido)
    saida = interface.abrir_historico("run_historico")
    assert saida[0] == item["query"]
    assert saida[1] == item["answer"]
    # Pergunta + saídas: estado original mantém os IDs para feedback.
    assert saida[10]["run_id"] == "run_historico"
    assert saida[10]["query_id"] == "q_historico"


def test_falha_ao_salvar_preserva_resposta(ambiente):
    item = resultado()
    ambiente.setattr(
        interface, "executar_pipeline",
        lambda *args, **kwargs: deepcopy(item),
    )

    def falhar(*args, **kwargs):
        raise OSError("Disco indisponível")

    avisos = []
    ambiente.setattr(interface, "salvar_consulta", falhar)
    ambiente.setattr(interface.gr, "Warning", avisos.append)
    saida = interface.executar(
        item["query"], 3, progress=lambda *a, **k: None
    )
    assert saida[0] == item["answer"]
    assert avisos


def test_historico_inexistente_nao_executa_consulta(ambiente):
    with pytest.raises(Exception, match="consulta salva"):
        interface.abrir_historico("inexistente")
