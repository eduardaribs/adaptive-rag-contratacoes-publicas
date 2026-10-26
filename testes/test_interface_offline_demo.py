import json

import pytest

from app import offline_demo, pipeline_adapter
from src import obs


@pytest.fixture
def ambiente_demo(tmp_path, monkeypatch):
    pasta = tmp_path / "data/raw/v3/agregada"
    pasta.mkdir(parents=True)
    for nome in (
        "itens_pe_038_26_2026.csv",
        "pca_2026_estado_rj.csv",
    ):
        (pasta / nome).write_text("fixture", encoding="utf-8")

    chunks = tmp_path / "chunks.json"
    chunks.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("RAG_DEMO_OFFLINE", "true")
    monkeypatch.setenv("RAG_DEMO_PACOTE", str(tmp_path))
    monkeypatch.setenv("RAG_DEMO_CHUNKS", str(chunks))
    monkeypatch.setenv("RAG_DEMO_COMMIT", "commit_teste")
    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path / "logs")

    def proibido(*args, **kwargs):
        raise AssertionError("A demonstração não deve chamar modelos.")

    monkeypatch.setattr(pipeline_adapter, "executar_consulta", proibido)
    monkeypatch.setattr(pipeline_adapter, "gerar_resposta", proibido)

    chamadas = []

    def executar(pergunta, plano, **kwargs):
        chamadas.append((plano, kwargs))
        resultado = {
            "estrategia": "consulta_agregada",
            "routes": ["agregada"],
            "query": pergunta,
            "query_id": plano["query_id"],
            "run_id": kwargs["run_id"],
            "operacao": plano["operacao"],
            "filtros_aplicados": plano["filtros"],
            "fontes": [plano["arquivo"]],
            "latencia_ms": 1,
            "soma_completa": True,
        }
        if plano["operacao"] == "resumir_pca":
            resultado.update(
                total_itens=2,
                valor_total_estimado="10.0001",
                itens_sem_valor=0,
            )
        else:
            resultado.update(
                itens_total=19, homologados=8,
                fracassados=9, desertos=2,
                valor_total_homologado="141002.08",
                homologados_sem_valor=0,
            )
        if plano["operacao"] == "resumir_itens_vinculos":
            resultado.update(
                total_chunks_verificados=2,
                verificacao_vinculos={
                    "correspondencias": {"estruturada": []},
                    "observacao": "Não comprova inexistência de documentos.",
                },
            )
        return resultado

    monkeypatch.setattr(offline_demo, "executar_plano", executar)
    return chamadas, tmp_path


@pytest.mark.parametrize("caso,operacao", [
    ("P02", "resumir_itens"),
    ("P07", "resumir_pca"),
    ("M01", "resumir_itens_vinculos"),
])
def test_demo_integra_interface_sem_modelos(ambiente_demo, caso, operacao):
    chamadas, pasta = ambiente_demo
    resultado = pipeline_adapter.executar_pipeline(
        offline_demo.PERGUNTAS[caso]
    )

    assert resultado["executado"] is True
    assert resultado["modo_demonstracao"] == "offline"
    assert resultado["commit_demonstracao"] == "commit_teste"
    assert resultado["operacao"] == operacao
    assert resultado["query_id"].startswith("q_demo_")
    assert resultado["run_id"]
    assert len(chamadas) == 1
    assert chamadas[0][0]["operacao"] == operacao
    assert chamadas[0][1]["run_id"] == resultado["run_id"]
    assert resultado["fontes_agregadas"]

    eventos = [
        json.loads(linha)
        for arquivo in (pasta / "logs").glob("pipeline-*.jsonl")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
    ]
    roteamento = [e for e in eventos if e["stage"] == "roteamento"]
    assert len(roteamento) == 1
    assert roteamento[0]["output"]["roteador_llm_executado"] is False


def test_demo_nao_ignora_filtro_adicional(ambiente_demo):
    chamadas, _ = ambiente_demo
    pergunta = offline_demo.PERGUNTAS["P02"] + " Apenas do fornecedor X."
    resultado = pipeline_adapter.executar_pipeline(pergunta)

    assert resultado["executado"] is False
    assert resultado["necessita_esclarecimento"] is True
    assert resultado["modo_demonstracao"] == "offline"
    assert chamadas == []


def test_demo_sinaliza_arquivo_ausente(ambiente_demo):
    chamadas, pasta = ambiente_demo
    (pasta / "data/raw/v3/agregada/pca_2026_estado_rj.csv").unlink()

    with pytest.raises(FileNotFoundError, match="demonstração"):
        offline_demo.executar_demo(offline_demo.PERGUNTAS["P07"])

    assert chamadas == []
