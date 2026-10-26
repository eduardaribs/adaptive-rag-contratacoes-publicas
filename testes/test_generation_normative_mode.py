import json
from types import SimpleNamespace

import pytest

from src import generate as gerador


CASOS = [
    (
        ["normativa"],
        ["normativa"],
        "Explique a regra.",
    ),
    (
        ["normativa"],
        ["normativa", "conversacional"],
        "Explique a regra.",
    ),
    (
        ["normativa", "conversacional"],
        ["normativa"],
        "Explique a regra.",
    ),
    (
        ["conversacional"],
        ["conversacional"],
        "O que a ata nº 191/2026 informa?",
    ),
    (
        ["conversacional", "estruturada"],
        ["conversacional", "estruturada"],
        "O que a ata nº 191/2026 informa e qual o controle PNCP?",
    ),
]


@pytest.mark.parametrize(
    "rotas,naturezas,pergunta",
    CASOS,
)
@pytest.mark.parametrize(
    "extrativo_explicito",
    [False, True],
)
def test_formato_so_muda_por_opcao_explicita(
    rotas,
    naturezas,
    pergunta,
    extrativo_explicito,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(gerador.obs, "PASTA_LOGS", tmp_path)
    chamadas = []

    def modelo(*, pergunta, contexto, client, modo_extrativo=False):
        chamadas.append(modo_extrativo)
        conteudo = (
            json.dumps({"chunk_ids": ["chunk_1"]})
            if modo_extrativo
            else "Regra documentada. [Fonte: chunk_1]"
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=conteudo),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

    monkeypatch.setattr(gerador, "chamar_llm", modelo)

    entrada = {
        "query": pergunta,
        "query_id": "q_modo_normativo",
        "routes": rotas,
        "filters": {},
        "is_refusal": False,
        "evidences": [
            {
                "chunk_id": f"chunk_{numero}",
                "text": "Regra documentada.",
                "source_file": "documento.txt",
                "natureza": natureza,
            }
            for numero, natureza in enumerate(naturezas, start=1)
        ],
        "stage": "fusao_rrf",
    }

    # Sem opção: exercita o padrão público da função.
    opcoes = (
        {"modo_extrativo": True}
        if extrativo_explicito
        else {}
    )
    resposta = gerador.gerar_resposta(
        entrada,
        client=object(),
        run_id="run_modo_normativo",
        **opcoes,
    )

    assert chamadas == [extrativo_explicito]
    assert resposta.stage == "geracao"
    assert [e.chunk_id for e in resposta.sources_used] == ["chunk_1"]
    assert "[Fonte: chunk_1]" in resposta.answer

    eventos = [
        json.loads(linha)
        for arquivo in tmp_path.glob("pipeline-*.jsonl")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    geracoes = [
        evento for evento in eventos
        if evento["stage"] == "geracao"
        and evento["status"] == "ok"
    ]
    assert geracoes

    formato = (
        "trechos_literais"
        if extrativo_explicito
        else "sintese_explicativa"
    )
    assert geracoes[-1]["output"]["formato_resposta"] == formato

    validacoes = [
        evento for evento in eventos
        if evento["stage"] == "validacao"
    ]
    tipos = {
        evento["input"]["tipo"]
        for evento in validacoes
    }
    assert "citacoes" in tipos
    assert all(evento["status"] == "ok" for evento in validacoes)

    if extrativo_explicito:
        assert "trechos_literais" in tipos
    else:
        assert resposta.answer == "Regra documentada. [Fonte: chunk_1]"
        assert "trechos_literais" not in tipos
