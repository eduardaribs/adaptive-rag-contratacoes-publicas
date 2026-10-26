import json
from types import SimpleNamespace

import pytest

from src.router import (
    _extrair_filtros_monetarios,
    _roteamento_fallback,
    analisar_consulta,
)
from src.retrieve import fusao_rrf


class ClienteFalso:
    def __init__(self, resposta_json):
        self.resposta_json = resposta_json
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=self._responder
            )
        )

    def _responder(self, **kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            self.resposta_json,
                            ensure_ascii=False,
                        )
                    )
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("acima de R$ 500 mil", 500000),
        ("superiores a R$ 1 milhão", 1000000),
        ("mais de R$ 1,5 milhão", 1500000),
        ("acima de R$ 750.000", 750000),
    ],
)
def test_conversao_valores_monetarios(
    pergunta,
    esperado,
):
    resultado = _extrair_filtros_monetarios(pergunta)

    assert resultado["valor_minimo"] == esperado


def test_pca_usa_rota_agregada_no_fallback():
    resultado = _roteamento_fallback(
        "Quais itens aparecem no Plano de "
        "Contratações Anual?"
    )

    assert "agregada" in resultado["routes"]
    assert "conversacional" not in resultado["routes"]


def test_ata_usa_rota_conversacional_no_fallback():
    resultado = _roteamento_fallback(
        "O que aparece nas atas de registro de preços?"
    )

    assert "conversacional" in resultado["routes"]


def test_fraude_gera_recusa_sem_rotas_no_fallback():
    resultado = _roteamento_fallback(
        "Esse contrato foi uma fraude?"
    )

    assert resultado["is_refusal"] is True
    assert resultado["routes"] == []


def test_valor_do_llm_e_corrigido_pela_pergunta():
    cliente = ClienteFalso({
        "routes": ["estruturada"],
        "filters": {
            "uf": "RJ",
            "ano": None,
            "valor_minimo": 500000000,
            "valor_maximo": None,
            "modalidade": None,
            "municipio": None,
            "fornecedor": None,
        },
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Teste.",
    })

    resultado = analisar_consulta(
        "Quais contratações acima de R$ 500 mil "
        "foram realizadas?",
        client=cliente,
    )

    assert resultado["filters"]["valor_minimo"] == 500000


def test_pca_e_corrigido_para_agregada():
    cliente = ClienteFalso({
        "routes": ["estruturada"],
        "filters": {
            "uf": "RJ",
            "ano": None,
            "valor_minimo": None,
            "valor_maximo": None,
            "modalidade": None,
            "municipio": None,
            "fornecedor": None,
        },
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Teste.",
    })

    resultado = analisar_consulta(
        "Quais itens aparecem no Plano de "
        "Contratações Anual?",
        client=cliente,
    )

    assert resultado["routes"] == ["agregada"]


def test_recusa_remove_rotas_e_filtros():
    cliente = ClienteFalso({
        "routes": ["normativa"],
        "filters": {
            "uf": "RJ",
            "ano": 2026,
            "valor_minimo": None,
            "valor_maximo": None,
            "modalidade": None,
            "municipio": None,
            "fornecedor": None,
        },
        "is_refusal": True,
        "refusal_reason": "Acusação de fraude.",
        "justification": "Teste.",
    })

    resultado = analisar_consulta(
        "Esse contrato foi uma fraude?",
        client=cliente,
    )

    assert resultado["is_refusal"] is True
    assert resultado["routes"] == []
    assert all(
        valor is None
        for valor in resultado["filters"].values()
    )


def test_rrf_funde_e_remove_duplicacoes():
    densos = [
        {"chunk_id": "a", "score": 0.9},
        {"chunk_id": "b", "score": 0.8},
    ]

    bm25 = [
        {"chunk_id": "b", "score": 5.0},
        {"chunk_id": "c", "score": 4.0},
    ]

    resultado = fusao_rrf(densos, bm25)

    ids = [item["chunk_id"] for item in resultado]

    assert ids[0] == "b"
    assert len(ids) == len(set(ids))
    assert set(ids) == {"a", "b", "c"}
