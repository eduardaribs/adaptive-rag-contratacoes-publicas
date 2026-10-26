from copy import deepcopy
import importlib

import pytest
from app import history_store


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    caminho = tmp_path / "historico.sqlite3"
    monkeypatch.setenv("HISTORY_PATH", str(caminho))
    return caminho


def resultado(run_id="run_1"):
    return {
        "run_id": run_id,
        "query_id": "q_1",
        "query": "Qual é o objeto?",
        "answer": "Objeto informado. [Fonte: documento_1]",
        "fontes": ["ata.pdf"],
        "evidences": [{"chunk_id": "documento_1", "trecho": "Objeto."}],
        "executado": True,
        "filters": {"ano_compra": 2026},
    }


def test_persiste_apos_recarregar_modulo(ambiente):
    original = resultado()
    copia = deepcopy(original)
    assert history_store.salvar_consulta(original)
    modulo = importlib.reload(history_store)
    assert modulo.carregar_consulta("run_1") == copia
    assert original == copia


def test_mesma_pergunta_execucoes_distintas(ambiente):
    history_store.salvar_consulta(resultado("run_1"))
    history_store.salvar_consulta(resultado("run_2"))
    assert len(history_store.listar_consultas()) == 2


def test_nao_sobrescreve_execucao_original(ambiente):
    original = resultado()
    history_store.salvar_consulta(original)
    alterado = {**original, "answer": "Outra resposta"}
    assert not history_store.salvar_consulta(alterado)
    assert history_store.carregar_consulta("run_1") == original


def test_leitura_vazia_nao_cria_banco(ambiente):
    assert history_store.listar_consultas() == []
    assert history_store.carregar_consulta("inexistente") is None
    assert not ambiente.exists()


def test_preserva_recusa_e_esclarecimento(ambiente):
    for numero, estrategia in enumerate(("recusa", "esclarecimento")):
        item = {
            **resultado(f"run_{numero}"),
            "executado": False,
            "estrategia": estrategia,
            "is_refusal": estrategia == "recusa",
            "fontes": [],
            "evidences": [],
        }
        history_store.salvar_consulta(item)
        assert history_store.carregar_consulta(item["run_id"]) == item


@pytest.mark.parametrize("campo", ["run_id", "query_id", "query", "answer"])
def test_rejeita_identificacao_incompleta(ambiente, campo):
    item = resultado()
    item.pop(campo)
    with pytest.raises(ValueError):
        history_store.salvar_consulta(item)
    assert not ambiente.exists()


def test_listagem_respeita_limite(ambiente):
    for numero in range(3):
        history_store.salvar_consulta(resultado(f"run_{numero}"))
    lista = history_store.listar_consultas(limite=2)
    assert [item["run_id"] for item in lista] == ["run_2", "run_1"]
    assert "resultado" not in lista[0]
