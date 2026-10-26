import json
from types import SimpleNamespace

import pytest

from src import generate
from src.grounded_synthesis import renderizar_sintese


def test_renderiza_explicacoes_com_referencias_por_bloco():
    entrada = json.dumps({"blocos": [
        {"texto": "Primeira informação.", "chunk_ids": ["a"]},
        {"texto": "Segunda informação.", "chunk_ids": ["b"]},
    ]})
    assert renderizar_sintese(entrada, ["a", "b"]) == (
        "Primeira informação. [Fonte: a]\n\n"
        "Segunda informação. [Fonte: b]"
    )


@pytest.mark.parametrize("dados", [
    {"blocos": []},
    {"blocos": [{"texto": "Afirmação.", "chunk_ids": []}]},
    {"blocos": [{"texto": "Afirmação.", "chunk_ids": ["inventado"]}]},
    {"blocos": [{"texto": "", "chunk_ids": ["a"]}]},
    {"blocos": [{"texto": "Afirmação.", "chunk_ids": [1]}]},
    {"blocos": [{"texto": "Afirmação.", "chunk_ids": ["a", "a"]}]},
    {"blocos": [{"texto": "Texto [Fonte: b]", "chunk_ids": ["a"]}]},
    {"blocos": [{"texto": "Afirmação.", "chunk_ids": ["a"], "extra": 1}]},
    {"blocos": "formato incorreto"},
    {"blocos": [], "extra": 1},
])
def test_rejeita_estrutura_ou_referencias_invalidas(dados):
    with pytest.raises(ValueError):
        renderizar_sintese(json.dumps(dados), ["a"])


def test_rejeita_prosa_fora_do_contrato():
    with pytest.raises(ValueError):
        renderizar_sintese("Resposta sem estrutura.", ["a"])


def test_chamada_real_do_contrato_renderiza_e_limita_ids():
    chamadas = []

    def criar(**kwargs):
        chamadas.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=json.dumps({"blocos": [
                {"texto": "Explicação documentada.", "chunk_ids": ["a"]}
            ]})),
        )])

    cliente = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))
    resposta = generate.chamar_llm(
        pergunta="Explique.",
        contexto="Chunk ID: a\nConteúdo: Informação.",
        client=cliente,
    )
    assert resposta.choices[0].message.content == (
        "Explicação documentada. [Fonte: a]"
    )
    formato = chamadas[0]["response_format"]
    assert formato["json_schema"]["name"] == "sintese_com_evidencias"
    item = formato["json_schema"]["schema"]["properties"]["blocos"]["items"]
    assert item["properties"]["chunk_ids"]["items"]["enum"] == ["a"]


def test_rejeita_resposta_cortada():
    def criar(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="length",
            message=SimpleNamespace(content='{"blocos": []}'),
        )])

    cliente = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=criar)
    ))
    with pytest.raises(ValueError, match="não concluída"):
        generate.chamar_llm(
            pergunta="Explique.",
            contexto="Chunk ID: a\nConteúdo: Informação.",
            client=cliente,
        )
