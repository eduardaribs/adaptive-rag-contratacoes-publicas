import json
from types import SimpleNamespace

import pytest

from src import generate
from src.schema import RetrievalResult, SourceEvidence


def evidencias():
    return [
        SourceEvidence(
            chunk_id="lei_29",
            source_file="lei.html",
            text="Trecho sobre pregão.",
        ),
        SourceEvidence(
            chunk_id="lei_4",
            source_file="lei.html",
            text="Trecho sobre microempresas.",
        ),
        SourceEvidence(
            chunk_id="ata_1",
            source_file="ata.txt",
            text="Trecho da reunião.",
        ),
    ]


def test_citacao_de_chunk_seleciona_apenas_chunk_citado():
    fontes = generate.validar_citacoes(
        "Regra. [Fonte: lei_29]", evidencias()
    )
    assert [e.chunk_id for e in fontes] == ["lei_29"]


def test_citacao_de_arquivo_preserva_chunks_da_fonte():
    fontes = generate.validar_citacoes(
        "Regra. [Fonte: lei.html]", evidencias()
    )
    assert [e.chunk_id for e in fontes] == ["lei_29", "lei_4"]


@pytest.mark.parametrize("resposta", [
    "Regra sem citação.",
    "Regra. [Fonte: todas as evidências]",
    "Regra. [Fonte: arquivo_inexistente.html]",
    "Regra. [Fonte: lei_29] Outra. [Fonte: inexistente]",
    "Regra. [Fonte: ]",
])
def test_citacoes_ausentes_ou_invalidas_sao_rejeitadas(resposta):
    with pytest.raises(ValueError):
        generate.validar_citacoes(resposta, evidencias())


@pytest.mark.parametrize("valida", [True, False])
def test_geracao_valida_citacoes_preserva_tokens_e_ids(
    monkeypatch, tmp_path, valida
):
    monkeypatch.setattr(generate.obs, "PASTA_LOGS", tmp_path)

    texto = (
        "Regra. [Fonte: lei_29]"
        if valida else
        "Regra. [Fonte: todas as evidências]"
    )
    resposta_mock = SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=texto))
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )
    monkeypatch.setattr(
        generate,
        "chamar_llm",
        lambda **kwargs: resposta_mock,
    )

    recuperacao = RetrievalResult(
        query="Explique a regra.",
        query_id="q_citacoes",
        routes=["normativa"],
        evidences=evidencias(),
    )

    resposta = generate.gerar_resposta(
        recuperacao,
        client=object(),
        run_id="run_citacoes",
    )

    assert resposta.query_id == "q_citacoes"
    assert resposta.query == recuperacao.query
    assert resposta.tokens.total == 15
    assert resposta.is_refusal is False

    if valida:
        assert resposta.answer == texto
        assert [e.chunk_id for e in resposta.sources_used] == ["lei_29"]
    else:
        assert resposta.sources_used == []
        assert resposta.confidence_level == "baixa"
        assert resposta.stage == "validacao"
        assert "Não foi possível apresentar" in resposta.answer

    eventos = [
        json.loads(linha)
        for caminho in tmp_path.glob("pipeline-*.jsonl")
        for linha in caminho.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    validacoes = [
        e for e in eventos
        if e["stage"] == "validacao"
        and e["input"].get("tipo") == "citacoes"
    ]

    assert len(validacoes) == 1
    evento = validacoes[0]
    assert evento["run_id"] == "run_citacoes"
    assert evento["query_id"] == "q_citacoes"
    assert evento["status"] == ("ok" if valida else "erro")
    assert "Trecho sobre pregão." not in json.dumps(
        evento, ensure_ascii=False
    )
