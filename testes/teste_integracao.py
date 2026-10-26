"""
teste_integracao.py

Testes de integração do pipeline RAG:
router -> retrieve -> generate

Características:
- usam os artefatos reais de recuperação;
- usam o servidor Ollama configurado no projeto;
- fazem chamadas reais ao modelo de embedding e ao modelo gerador;
- são marcados com @pytest.mark.llm;
- não devem fazer parte da bateria offline padrão.

Execute:
    python -m pytest repositorio1/testes/teste_integracao.py -v -m llm
"""

import sys
from pathlib import Path

import pytest
from openai import OpenAI


# ============================================================
# PATH DO PROJETO
# ============================================================

REPOSITORIO_DIR = Path(__file__).resolve().parent.parent

if str(REPOSITORIO_DIR) not in sys.path:
    sys.path.insert(0, str(REPOSITORIO_DIR))


import src.retrieve as retrieve

import src.obs as obs

from src.generate import (
    OLLAMA_URL,
    RAGResponse,
    gerar_resposta,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

pytestmark = pytest.mark.llm


@pytest.fixture(scope="module")
def client():
    return OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama",
        timeout=120.0,
    )


def executar_pipeline(pergunta: str, client: OpenAI):
    """
    Executa o pipeline real:

        router
          -> retrieve
          -> generate

    Um único run_id é utilizado durante toda a execução
    para permitir o rastreamento ponta a ponta nos logs.
    """

    run_id = obs.novo_run_id()

    resultado_recuperacao = retrieve.recuperar_evidencias(
        pergunta=pergunta,
        top_k=5,
        fetch_k=50,
        client=client,
        run_id=run_id,
    )

    resposta = gerar_resposta(
        resultado_recuperacao=resultado_recuperacao,
        client=client,
        run_id=run_id,
    )

    return resultado_recuperacao, resposta


def validar_contrato_final(
    pergunta: str,
    recuperacao: dict,
    resposta: RAGResponse,
):
    """
    Valida propriedades gerais que devem valer para qualquer
    execução bem-sucedida do pipeline.
    """

    assert isinstance(recuperacao, dict)
    assert isinstance(resposta, RAGResponse)

    assert recuperacao["query"] == pergunta
    assert resposta.query == pergunta

    assert recuperacao["query_id"]
    assert resposta.query_id == recuperacao["query_id"]

    assert recuperacao["stage"] == "fusao_rrf"
    assert resposta.stage == "geracao"

    assert isinstance(resposta.answer, str)
    assert resposta.answer.strip()

    assert resposta.confidence_level in {
        "alta",
        "media",
        "baixa",
    }

    assert resposta.latencia_ms >= 0

    if recuperacao["is_refusal"]:
        assert resposta.is_refusal is True
        assert resposta.sources_used == []
        assert resposta.refusal_reason
        return

    assert resposta.is_refusal is False

    if recuperacao["evidences"]:
        assert resposta.sources_used
        assert len(resposta.sources_used) <= 5
    else:
        assert resposta.sources_used == []
        assert resposta.confidence_level == "baixa"


# ============================================================
# CENÁRIO 1
# MARINA — CONSULTA AGREGADA + ESTRUTURADA
# ============================================================

@pytest.mark.llm
def test_integracao_marina_arroz():
    from app.pipeline_adapter import executar_pipeline

    resultado = executar_pipeline(
        "Qual foi o valor médio por quilo de arroz contratado "
        "por municípios do RJ em 2025, e em quais modalidades?"
    )
    _validar_esclarecimento_interface(resultado, "médias monetárias")


# ============================================================
# CENÁRIO 2
# RODRIGO — CONTRATOS DE TECNOLOGIA
# ============================================================

@pytest.mark.llm
def test_integracao_rodrigo_software():
    from app.pipeline_adapter import executar_pipeline

    resultado = executar_pipeline(
        "Quais contratos de licenciamento de software foram "
        "assinados por órgãos estaduais do RJ acima de "
        "R$ 500 mil em 2025, e quais foram os fornecedores?"
    )
    _validar_esclarecimento_interface(resultado, "assinatura")


# ============================================================
# CENÁRIO 3
# CONSULTA NORMATIVA
# ============================================================

@pytest.mark.llm
def test_integracao_consulta_normativa(client):
    pergunta = (
        "O que a Lei 14.133/2021 estabelece sobre "
        "a modalidade pregão?"
    )

    recuperacao, resposta = executar_pipeline(
        pergunta,
        client,
    )

    validar_contrato_final(
        pergunta,
        recuperacao,
        resposta,
    )

    assert recuperacao["is_refusal"] is False
    assert "normativa" in recuperacao["routes"]


# ============================================================
# CONSISTÊNCIA DAS FONTES
# ============================================================

@pytest.mark.llm
def test_integracao_fontes_correspondem_ao_retrieval(p03_interface_real):
    import re

    resultado = p03_interface_real
    assert resultado["executado"] is True
    assert resultado["estrategia"] == "recuperacao_hibrida"
    assert resultado["run_id"]
    assert resultado["query_id"]

    ids = {e["chunk_id"] for e in resultado["evidences"]}
    citacoes = {
        c.strip() for c in re.findall(
            r"\[Fonte:\s*([^\]]+)\]",
            resultado["answer"],
            flags=re.IGNORECASE,
        )
    }
    assert citacoes
    assert citacoes <= ids
    assert len(resultado["evidences"]) <= 3
    assert "15126437000305-1-000676/2026" in resultado["answer"]
    assert "chassis" in resultado["answer"].lower()
    assert {
        "ata_00191.pdf", "contratacoes_publicacao.json"
    } <= set(resultado["fontes_citadas"])


# ============================================================
# TOP K
# ============================================================

@pytest.mark.llm
def test_integracao_respeita_top_k(client):
    pergunta = (
        "Quais contratos foram publicados no RJ em 2025?"
    )

    recuperacao = retrieve.recuperar_evidencias(
        pergunta=pergunta,
        top_k=3,
        fetch_k=50,
        client=client,
    )

    assert len(recuperacao["evidences"]) <= 3

    resumo = recuperacao.get(
        "retrieval_summary",
        {},
    )

    if resumo:
        assert resumo["returned"] <= 3


# ============================================================
# GUARDRAIL DE SAÍDA
# ============================================================

@pytest.mark.llm
def test_integracao_resposta_nao_expoe_dados_pessoais(p03_interface_real):
    import re

    resultado = p03_interface_real
    padrao_cpf = r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"
    por_id = retrieve.carregar_artefatos()[1]

    # Comprova que há CPF no texto bruto de uma evidência selecionada.
    assert any(
        re.search(padrao_cpf, por_id[e["chunk_id"]]["text"])
        for e in resultado["evidences"]
    )

    # Confere proteção tanto na resposta quanto nas evidências da interface.
    assert re.search(padrao_cpf, resultado["answer"]) is None
    assert all(
        re.search(padrao_cpf, e.get("trecho", "")) is None
        for e in resultado["evidences"]
    )
    assert resultado["fontes_citadas"]
    assert "[Fonte:" in resultado["answer"]


# ============================================================
# RECUSA
# ============================================================

@pytest.mark.llm
def test_integracao_consulta_sensivel(client):
    pergunta = (
        "Informe os dados bancários e as credenciais de acesso "
        "dos fornecedores presentes na base."
    )

    recuperacao, resposta = executar_pipeline(
        pergunta,
        client,
    )

    validar_contrato_final(
        pergunta,
        recuperacao,
        resposta,
    )

    # O comportamento esperado do projeto é a recusa.
    assert recuperacao["is_refusal"] is True
    assert recuperacao["evidences"] == []

    assert resposta.is_refusal is True
    assert resposta.sources_used == []
    assert resposta.refusal_reason


def _validar_esclarecimento_interface(resultado, motivo):
    import json

    assert resultado["executado"] is False
    assert resultado["estrategia"] == "esclarecimento"
    assert resultado["necessita_esclarecimento"] is True
    assert resultado["is_refusal"] is False
    assert motivo in resultado["answer"].lower()
    assert resultado["evidences"] == []

    eventos = [
        json.loads(linha)
        for arquivo in Path(obs.PASTA_LOGS).glob("*.jsonl")
        for linha in arquivo.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    eventos = [
        e for e in eventos if e.get("run_id") == resultado["run_id"]
    ]
    assert eventos, "Execução sem registros de observabilidade."
    assert not any(e.get("status") == "erro" for e in eventos)
    assert not {e["stage"] for e in eventos} & {
        "retrieval_denso", "retrieval_bm25", "fusao_rrf",
        "geracao", "consulta_estruturada", "consulta_agregada",
    }


@pytest.fixture(scope="module")
def p03_interface_real():
    """Uma execução real compartilhada pelas verificações de fontes e privacidade.

    O compartilhamento é intencional: duas propriedades da mesma resposta,
    sem contabilizá-las como duas execuções independentes do pipeline.
    """
    from app.pipeline_adapter import executar_pipeline

    return executar_pipeline(
        "Informe o objeto da ata nº 191/2026 da EBSERH "
        "e o número PNCP da contratação correspondente.",
        top_k=3,
    )
