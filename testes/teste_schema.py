"""
teste_schema.py

Testes de contrato e validação dos modelos Pydantic definidos em src/schema.py.

Os testes são offline e não dependem de API, LLM ou conexão com a internet.
"""

import pytest
from pydantic import ValidationError

from src.schema import (
    QueryFilters,
    RAGResponse,
    RetrievalResult,
    SourceEvidence,
    TokenUsage,
)


def criar_evidencia() -> SourceEvidence:
    """Cria uma evidência válida reutilizada pelos testes."""
    return SourceEvidence(
        chunk_id="fixture_pncp_001",
        text=(
            "A empresa Exemplo Tecnologia Ltda. celebrou contrato "
            "no valor de R$ 650.000,00."
        ),
        rrf_score=0.0325,
        retrieval_sources=["dense", "bm25"],
        source_file="contratacoes_fixture.json",
        doc_type="contratacao",
        sensitivity="publico",
        base_id="estruturada_pncp_rj",
        natureza="estruturada",
        metadata={
            "uf": "RJ",
            "ano": 2025,
            "valor": 650000,
        },
    )


def test_query_filters_valido():
    filtros = QueryFilters(
        uf="RJ",
        ano=2025,
        valor_minimo=500000,
        valor_maximo=1000000,
        modalidade="Pregão - Eletrônico",
        municipio="Rio de Janeiro",
        fornecedor="Exemplo Tecnologia Ltda.",
    )

    assert filtros.uf == "RJ"
    assert filtros.ano == 2025
    assert filtros.valor_minimo == 500000
    assert filtros.valor_maximo == 1000000
    assert filtros.modalidade == "Pregão - Eletrônico"
    assert filtros.municipio == "Rio de Janeiro"
    assert filtros.fornecedor == "Exemplo Tecnologia Ltda."


def test_source_evidence_valida():
    evidencia = criar_evidencia()

    assert evidencia.chunk_id == "fixture_pncp_001"
    assert evidencia.doc_type == "contratacao"
    assert evidencia.sensitivity == "publico"
    assert evidencia.base_id == "estruturada_pncp_rj"
    assert evidencia.natureza == "estruturada"
    assert evidencia.metadata["uf"] == "RJ"


def test_retrieval_result_valido():
    evidencia = criar_evidencia()

    resultado = RetrievalResult(
        query="Quais contratos de tecnologia ficaram acima de R$ 500 mil?",
        query_id="q_schema_001",
        routes=["estruturada"],
        filters=QueryFilters(
            uf="RJ",
            ano=2025,
            valor_minimo=500000,
        ),
        evidences=[evidencia],
    )

    assert resultado.is_refusal is False
    assert len(resultado.evidences) == 1
    assert resultado.evidences[0].chunk_id == evidencia.chunk_id


def test_retrieval_result_recusa_valida():
    resultado = RetrievalResult(
        query="Informe dados bancários de um fornecedor.",
        query_id="q_schema_002",
        routes=[],
        is_refusal=True,
        refusal_reason="Solicitação envolve dados sensíveis.",
        evidences=[],
    )

    assert resultado.is_refusal is True
    assert resultado.evidences == []
    assert resultado.refusal_reason is not None


def test_retrieval_recusa_com_evidencia_deve_falhar():
    evidencia = criar_evidencia()

    with pytest.raises(ValidationError):
        RetrievalResult(
            query="Informe dados bancários de um fornecedor.",
            query_id="q_schema_003",
            routes=["estruturada"],
            is_refusal=True,
            refusal_reason="Solicitação envolve dados sensíveis.",
            evidences=[evidencia],
        )


def test_rag_response_valida():
    evidencia = criar_evidencia()

    resposta = RAGResponse(
        query="Quais contratos de tecnologia ficaram acima de R$ 500 mil?",
        query_id="q_schema_004",
        answer=(
            "Foi encontrado um contrato da Exemplo Tecnologia Ltda. "
            "no valor de R$ 650.000,00."
        ),
        confidence_level="alta",
        sources_used=[evidencia],
        tokens=TokenUsage(
            prompt=150,
            completion=50,
            total=200,
        ),
        modelo="qcwind/qwen3-8b-instruct-Q4-K-M",
        latencia_ms=850.5,
    )

    assert resposta.is_refusal is False
    assert resposta.confidence_level == "alta"
    assert len(resposta.sources_used) == 1
    assert resposta.tokens.total == 200


def test_rag_response_recusa_valida():
    resposta = RAGResponse(
        query="Informe a conta bancária do fornecedor.",
        query_id="q_schema_005",
        answer="Não posso fornecer dados bancários.",
        confidence_level="alta",
        sources_used=[],
        is_refusal=True,
        refusal_reason="Solicitação envolve dados sensíveis.",
    )

    assert resposta.is_refusal is True
    assert resposta.sources_used == []
    assert resposta.refusal_reason is not None


def test_rag_response_recusa_com_fonte_deve_falhar():
    evidencia = criar_evidencia()

    with pytest.raises(ValidationError):
        RAGResponse(
            query="Informe a conta bancária do fornecedor.",
            query_id="q_schema_006",
            answer="Não posso fornecer dados bancários.",
            confidence_level="alta",
            sources_used=[evidencia],
            is_refusal=True,
            refusal_reason="Solicitação envolve dados sensíveis.",
        )


def test_rag_response_recusa_sem_motivo_deve_falhar():
    with pytest.raises(ValidationError):
        RAGResponse(
            query="Informe dados sensíveis.",
            query_id="q_schema_007",
            answer="Não posso fornecer essa informação.",
            confidence_level="alta",
            sources_used=[],
            is_refusal=True,
            refusal_reason=None,
        )


def test_rag_response_vazia_deve_falhar():
    with pytest.raises(ValidationError):
        RAGResponse(
            query="Quais contratos foram encontrados?",
            query_id="q_schema_008",
            answer="   ",
            confidence_level="baixa",
            sources_used=[],
            is_refusal=False,
        )
