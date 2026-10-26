import json
from types import SimpleNamespace

import pytest

from src import generate


@pytest.mark.parametrize("chunk_citado, valido", [
    ("lei_29", True),
    ("lei_999", False),
])
def test_geracao_extrativa_verifica_chunk_e_preserva_tokens(
    monkeypatch, tmp_path, chunk_citado, valido
):
    monkeypatch.chdir(tmp_path)

    trecho = (
        "Adota-se o pregão quando o objeto possuir padrões "
        "de desempenho e qualidade objetivamente definidos."
    )
    recuperacao = {
        "query": "Quando se aplica o pregão?",
        "query_id": "q_extrativa",
        "routes": ["normativa"],
        "filters": {},
        "evidences": [
            {
                "chunk_id": "lei_28",
                "text": "São modalidades de licitação: I - pregão;",
                "source_file": "lei.html",
                "natureza": "normativa",
            },
            {
                "chunk_id": "lei_29",
                "text": trecho,
                "source_file": "lei.html",
                "natureza": "normativa",
            },
        ],
    }

    chamadas = []

    def chamar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps({
                            "chunk_ids": [chunk_citado]
                        })
                    )
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )

    monkeypatch.setattr(generate, "chamar_llm", chamar)

    resultado = generate.gerar_resposta(
        recuperacao,
        client=object(),
        run_id="run_extrativa",
        modo_extrativo=True,
    )

    assert chamadas[0]["modo_extrativo"] is True
    assert resultado.query_id == "q_extrativa"
    assert resultado.tokens.total == 15

    if valido:
        assert trecho in resultado.answer
        assert "[Fonte: lei_29]" in resultado.answer
        assert [e.chunk_id for e in resultado.sources_used] == ["lei_29"]
    else:
        assert resultado.stage == "validacao"
        assert resultado.sources_used == []
        assert trecho not in resultado.answer
