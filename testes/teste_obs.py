import json

import pytest

from src import obs


def test_registrar_falha_no_log(tmp_path, monkeypatch):
    """
    Verifica se uma exceção durante uma etapa é registrada
    no log com status='erro'.
    """

    # Redireciona os logs do teste para uma pasta temporária
    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path)

    run_id = "run_teste_erro"
    query_id = "q_teste_erro"

    with pytest.raises(RuntimeError):

        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="geracao",
            input_data={
                "query": "Pergunta de teste"
            },
            modelo="modelo_teste",
        ):
            # Simula uma falha do modelo
            raise RuntimeError("Falha simulada do LLM")

    arquivos = list(tmp_path.glob("pipeline-*.jsonl"))

    assert len(arquivos) == 1

    with arquivos[0].open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        linhas = arquivo.readlines()

    assert len(linhas) == 1

    evento = json.loads(linhas[0])

    assert evento["run_id"] == run_id
    assert evento["query_id"] == query_id

    assert evento["stage"] == "geracao"
    assert evento["status"] == "erro"

    assert evento["modelo"] == "modelo_teste"

    assert evento["output"]["erro"] == "RuntimeError"
    assert (
        evento["output"]["mensagem"]
        == "Falha simulada do LLM"
    )