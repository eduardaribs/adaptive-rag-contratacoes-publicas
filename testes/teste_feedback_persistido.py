"""Testes da persistência de feedback da interface."""

import json

from app.feedback_store import registrar_feedback


def test_feedback_e_acrescentado_ao_jsonl(
    tmp_path,
    monkeypatch,
):
    caminho = tmp_path / "feedback.jsonl"

    monkeypatch.setenv(
        "FEEDBACK_PATH",
        str(caminho),
    )

    status = """
    **Run ID:** run_teste
    **Query ID:** query_teste
    """

    mensagem = registrar_feedback(
        pergunta="Quais contratações envolvem tecnologia?",
        avaliacao="util",
        comentario="Resposta adequada.",
        rota="estruturada",
        evidencias=[
            {
                "fonte": "contratacoes_publicacao.json",
            }
        ],
        status=status,
    )

    assert caminho.exists()
    assert "salvo" in mensagem.lower()

    linhas = caminho.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(linhas) == 1

    registro = json.loads(linhas[0])

    assert registro["avaliacao"] == "util"
    assert registro["query_id"] == "query_teste"
    assert registro["run_id"] == "run_teste"
    assert registro["rota"] == "estruturada"
    assert registro["fontes"] == [
        "contratacoes_publicacao.json"
    ]


def test_feedback_nao_apaga_registro_anterior(
    tmp_path,
    monkeypatch,
):
    caminho = tmp_path / "feedback.jsonl"

    monkeypatch.setenv(
        "FEEDBACK_PATH",
        str(caminho),
    )

    for avaliacao in ["util", "nao_util"]:
        registrar_feedback(
            pergunta="Pergunta de teste",
            avaliacao=avaliacao,
            comentario="",
            rota="normativa",
            evidencias=[],
            status=(
                "**Run ID:** run_1\n"
                "**Query ID:** query_1"
            ),
        )

    linhas = caminho.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(linhas) == 2
