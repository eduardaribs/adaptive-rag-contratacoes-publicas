import json
from types import SimpleNamespace

import pytest

from src import generate
from src.schema import RetrievalResult, SourceEvidence


def executar_simulado(monkeypatch, tmp_path, conteudo):
    monkeypatch.setattr(generate.obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def chamar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=conteudo),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30,
            ),
        )

    monkeypatch.setattr(generate, "chamar_llm", chamar)

    evidencias = [
        SourceEvidence(
            chunk_id="registro.json_chunk_9",
            source_file="registro.json",
            natureza="estruturada",
            text="Objeto: equipamento. Controle PNCP: exemplo-1/2026.",
        ),
        SourceEvidence(
            chunk_id="documento.pdf_chunk_3",
            source_file="documento.pdf",
            natureza="conversacional",
            text=(
                "Ata nº 191/2026. Processo administrativo associado. "
                "CPF: 123.456.789-10."
            ),
        ),
        SourceEvidence(
            chunk_id="documento.pdf_chunk_5",
            source_file="documento.pdf",
            natureza="conversacional",
            text="Cláusulas gerais de execução.",
        ),
    ]

    recuperacao = RetrievalResult(
        query="O que a ata nº 191/2026 informa e qual o controle PNCP?",
        query_id="q_extrativo_offline",
        routes=["conversacional", "estruturada"],
        evidences=evidencias,
    )

    resposta = generate.gerar_resposta(
        recuperacao,
        client=object(),
        run_id="run_extrativo_offline",
        modo_extrativo=True,
    )

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    return resposta, chamadas, eventos


def test_selecao_valida_preserva_fontes_tokens_mascara_e_logs(
    monkeypatch, tmp_path
):
    resposta, chamadas, eventos = executar_simulado(
        monkeypatch,
        tmp_path,
        json.dumps({
            "chunk_ids": [
                "registro.json_chunk_9",
                "documento.pdf_chunk_3",
            ]
        }),
    )

    assert len(chamadas) == 1
    assert chamadas[0]["modo_extrativo"] is True
    assert resposta.query_id == "q_extrativo_offline"
    assert resposta.tokens.total == 30
    assert resposta.stage == "geracao"
    assert [e.chunk_id for e in resposta.sources_used] == [
        "registro.json_chunk_9",
        "documento.pdf_chunk_3",
    ]
    assert "[Fonte: registro.json_chunk_9]" in resposta.answer
    assert "[Fonte: documento.pdf_chunk_3]" in resposta.answer
    assert "Cláusulas gerais" not in resposta.answer
    assert "123.456.789-10" not in resposta.answer
    assert "[CPF_OCULTO]" in resposta.answer

    assert eventos
    assert all(
        e["run_id"] == "run_extrativo_offline"
        and e["query_id"] == "q_extrativo_offline"
        for e in eventos
    )
    validacoes = [
        e for e in eventos
        if e["stage"] == "validacao"
    ]
    assert {e["input"]["tipo"] for e in validacoes} == {
        "trechos_literais", "citacoes"
    }
    assert all(e["status"] == "ok" for e in validacoes)


@pytest.mark.parametrize("selecao", [
    '{"chunk_ids": [1, 3]}',
    '{"chunk_ids": ["inexistente"]}',
    '{"chunk_ids": ["documento.pdf"]}',
    '{"chunk_ids": []}',
    'Texto sem JSON.',
    '{"chunk_ids": ["documento.pdf_chunk_3"], "resposta": "extra"}',
])
def test_selecao_invalida_bloqueia_saida_e_registra_erro(
    monkeypatch, tmp_path, selecao
):
    resposta, chamadas, eventos = executar_simulado(
        monkeypatch, tmp_path, selecao
    )

    assert len(chamadas) == 1
    assert resposta.stage == "validacao"
    assert resposta.sources_used == []
    assert resposta.tokens.total == 30
    assert "Não foi possível apresentar" in resposta.answer
    assert "123.456.789-10" not in resposta.answer

    falhas = [
        e for e in eventos
        if e["stage"] == "validacao"
        and e["input"].get("tipo") == "trechos_literais"
        and e["status"] == "erro"
    ]
    assert len(falhas) == 1
    assert falhas[0]["run_id"] == "run_extrativo_offline"
    assert falhas[0]["query_id"] == "q_extrativo_offline"
