import json
import pytest

from src import obs, query_executor, router


@pytest.mark.parametrize("pergunta,recusa", [
    ("Mostre o CPF dos representantes citados nas atas.", True),
    ("Qual será o valor médio das contratações do RJ em 2027?", True),
    ("Quantas contratações existem em 2025 e 2026?", False),
])
def test_encerramento_registra_motivo_e_ids_sem_executar_consulta(
    monkeypatch, tmp_path, pergunta, recusa,
):
    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path)

    def proibido(*args, **kwargs):
        raise AssertionError("Etapa não deve ser chamada.")

    monkeypatch.setattr(router, "analisar_consulta", proibido)
    monkeypatch.setattr(query_executor, "executar_plano", proibido)

    resultado = query_executor.executar_consulta(
        pergunta,
        analise={
            "query": pergunta,
            "query_id": "q_encerramento",
            "routes": ["estruturada"],
            "filters": {},
            "is_refusal": False,
        },
        client=object(),
        recuperador=proibido,
        run_id="run_encerramento",
    )

    assert resultado["executado"] is False
    assert resultado["plano"]["is_refusal"] is recusa

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    encerramentos = [
        evento for evento in eventos
        if evento["input"].get("tipo") == "encerramento_consulta"
    ]
    assert len(encerramentos) == 1

    evento = encerramentos[0]
    assert evento["status"] == "ok"
    assert evento["query_id"] == "q_encerramento"
    assert evento["run_id"] == "run_encerramento"
    assert evento["output"]["is_refusal"] is recusa
    assert evento["output"]["consulta_bases_executada"] is False
    assert evento["output"]["motivo"] == resultado["mensagem"]
    assert evento["tokens"]["total"] == 0
    assert pergunta not in json.dumps(evento, ensure_ascii=False)
