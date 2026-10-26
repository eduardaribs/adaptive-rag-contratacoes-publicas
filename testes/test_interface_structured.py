from copy import deepcopy
import json

import pytest

from app.interface_results import (
    preparar_estruturado,
    tabela_consulta,
    mudar_pagina,
    feedback_da_consulta,
    status_consulta,
)


def resultado():
    return {
        "query": "Liste objetos",
        "query_id": "q_1",
        "run_id": "run_1",
        "estrategia": "consulta_estruturada",
        "operacao": "listar",
        "total": 3,
        "total_base": 5,
        "pagina": 1,
        "total_paginas": 2,
        "tamanho_pagina": 2,
        "campos": ["objeto"],
        "registros": [
            {"objeto": "A"},
            {"objeto": "B"},
        ],
        "filtros_aplicados": {"ano_compra": 2026},
        "fontes": ["teste.json"],
        "referencias": [],
        "plano": {
            "estrategia": "consulta_estruturada",
            "operacao": "listar",
            "bases": ["estruturada"],
            "pagina": 1,
            "filtros": {"ano_compra": 2026},
            "campos": ["objeto"],
        },
    }


def test_contagem_preserva_numero():
    r = resultado()
    r.update(
        operacao="contar",
        total=1234,
        registros=[],
        campos=[],
        pagina=None,
        total_paginas=0,
    )

    apresentado = preparar_estruturado(r)

    assert apresentado["total"] == 1234
    assert "1.234" in apresentado["answer"]
    assert apresentado["tokens"] == {}
    assert r.get("answer") is None


def test_tabela_mostra_somente_campos_solicitados():
    r = resultado()
    r["registros"][0]["campo_extra"] = "Não mostrar"

    assert tabela_consulta(r) == {
        "headers": ["objeto"],
        "data": [["A"], ["B"]],
    }


def test_pagina_reutiliza_plano_e_total(monkeypatch):
    from src import obs

    monkeypatch.setattr(
        obs,
        "novo_run_id",
        lambda: "run_2",
    )

    original = resultado()
    copia = deepcopy(original)

    def executar(pergunta, plano, **kwargs):
        assert pergunta == original["query"]
        assert plano["pagina"] == 2
        assert plano["filtros"] == original["plano"]["filtros"]
        assert kwargs["run_id"] == "run_2"

        r = resultado()
        r.update(
            pagina=2,
            registros=[{"objeto": "C"}],
            run_id="run_2",
        )
        return r

    r = mudar_pagina(original, 1, executor=executar)

    assert r["total"] == 3
    assert r["query_id"] == "q_1"
    assert r["run_id"] == "run_2"
    assert r["pagina"] == 2
    assert original == copia


def test_nao_executa_pagina_fora_dos_limites():
    def proibido(*args, **kwargs):
        raise AssertionError("Não executar.")

    r = mudar_pagina(resultado(), -1, executor=proibido)

    assert r["pagina"] == 1


def test_paginacao_detecta_mudanca_de_base():
    def executar(*args, **kwargs):
        r = resultado()
        r["total"] = 4
        return r

    with pytest.raises(ValueError, match="base mudou"):
        mudar_pagina(resultado(), 1, executor=executar)


def test_feedback_usa_consulta_guardada_e_fontes(
    tmp_path,
    monkeypatch,
):
    caminho = tmp_path / "feedback.jsonl"

    monkeypatch.setenv(
        "FEEDBACK_PATH",
        str(caminho),
    )

    r = preparar_estruturado(resultado())
    feedback_da_consulta(r, "Útil", "Conferido")

    registro = json.loads(
        caminho.read_text(encoding="utf-8")
    )

    assert registro["pergunta"] == "Liste objetos"
    assert registro["query_id"] == "q_1"
    assert registro["run_id"] == "run_1"
    assert registro["fontes"] == ["teste.json"]


def test_feedback_sem_consulta_nao_salva(
    tmp_path,
    monkeypatch,
):
    caminho = tmp_path / "feedback.jsonl"

    monkeypatch.setenv(
        "FEEDBACK_PATH",
        str(caminho),
    )

    mensagem = feedback_da_consulta({}, "Útil", "")

    assert "Faça uma consulta" in mensagem
    assert not caminho.exists()


def test_contagem_nao_exibe_evidencias_no_status():
    r = preparar_estruturado(resultado())

    assert "Evidências solicitadas" not in status_consulta(r)
