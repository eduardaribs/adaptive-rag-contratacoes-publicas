"""Testes da validação do filtro de UF no roteador."""

from src.router import (
    _extrair_uf_explicita,
    _roteamento_fallback,
    _validar_filtros_contra_pergunta,
)


def test_remove_uf_inventada_pelo_modelo():
    filtros = {
        "uf": "RJ",
        "ano": None,
        "valor_minimo": None,
        "valor_maximo": None,
        "modalidade": None,
        "municipio": None,
        "fornecedor": None,
    }

    resultado = _validar_filtros_contra_pergunta(
        "O que foi registrado nas atas sobre aquisições?",
        filtros,
    )

    assert resultado["uf"] is None


def test_aceita_sigla_rj_explicitamente():
    assert (
        _extrair_uf_explicita(
            "Quais contratações foram publicadas no RJ?"
        )
        == "RJ"
    )


def test_aceita_nome_rio_de_janeiro_explicitamente():
    assert (
        _extrair_uf_explicita(
            "Quais atas são do Rio de Janeiro?"
        )
        == "RJ"
    )


def test_fallback_nao_inventa_uf():
    resultado = _roteamento_fallback(
        "O que foi registrado nas atas sobre aquisições?"
    )

    assert resultado["filters"]["uf"] is None
