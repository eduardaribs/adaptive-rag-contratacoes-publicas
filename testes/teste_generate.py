"""
teste_generate.py

Testes unitários e de contrato para src/generate.py.

Os testes não dependem do servidor Ollama.
As respostas do LLM são simuladas localmente.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import generate
from src.schema import (
    RetrievalResult,
    SourceEvidence,
)


# ============================================================
# Fixtures auxiliares
# ============================================================

@pytest.fixture
def evidencia():
    return SourceEvidence(
        chunk_id="chunk_001",
        text=(
            "A empresa Exemplo Tecnologia Ltda. possui contrato "
            "no valor de R$ 650.000,00."
        ),
        rrf_score=0.03,
        retrieval_sources=["dense", "bm25"],
        source_file="contratos_2025.csv",
        doc_type="contrato",
        sensitivity="publico",
        base_id="estruturada_pncp_rj",
        natureza="estruturada",
        metadata={
            "uf": "RJ",
            "ano": 2025,
            "valor": 650000,
        },
    )


@pytest.fixture
def resultado_com_evidencia(evidencia):
    return RetrievalResult(
        query=(
            "Quais contratos de tecnologia ficaram "
            "acima de R$ 500 mil em 2025?"
        ),
        query_id="q_teste_001",
        routes=["estruturada"],
        filters={
            "uf": "RJ",
            "ano": 2025,
            "valor_minimo": 500000,
        },
        is_refusal=False,
        refusal_reason=None,
        evidences=[evidencia],
    )


@pytest.fixture
def resposta_llm():
    """
    Simula o objeto retornado pela API OpenAI/Ollama.
    """

    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "A empresa Exemplo Tecnologia Ltda. possui "
                        "contrato de R$ 650.000,00. "
                        "[Fonte: contratos_2025.csv]"
                    )
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
        ),
    )


# ============================================================
# Contexto
# ============================================================

def test_montar_contexto(evidencia):
    contexto = generate.montar_contexto(
        [evidencia]
    )

    assert "EVIDÊNCIA 1" in contexto
    assert "contratos_2025.csv" in contexto
    assert "estruturada_pncp_rj" in contexto
    assert "chunk_001" in contexto
    assert "R$ 650.000,00" in contexto


# ============================================================
# Confiança
# ============================================================

def test_confianca_baixa_sem_evidencias():
    assert generate.calcular_confianca([]) == "baixa"


def test_confianca_baixa_com_uma_evidencia(evidencia):
    assert (
        generate.calcular_confianca(
            [evidencia]
        )
        == "baixa"
    )


def test_confianca_media_com_duas_evidencias(evidencia):
    evidencia_2 = evidencia.model_copy(
        update={
            "chunk_id": "chunk_002",
        }
    )

    assert (
        generate.calcular_confianca(
            [
                evidencia,
                evidencia_2,
            ]
        )
        == "media"
    )


def test_confianca_alta_com_tres_evidencias():
    evidencias = [
        SourceEvidence(
            chunk_id="chunk_001",
            text="Contrato A",
            source_file="fonte_a.csv",
        ),
        SourceEvidence(
            chunk_id="chunk_002",
            text="Contrato B",
            source_file="fonte_b.csv",
        ),
        SourceEvidence(
            chunk_id="chunk_003",
            text="Contrato C",
            source_file="fonte_a.csv",
        ),
    ]

    assert (
        generate.calcular_confianca(
            evidencias
        )
        == "alta"
    )


# ============================================================
# Guardrail de dados pessoais
# ============================================================

def test_mascarar_cpf():
    texto = "CPF do responsável: 123.456.789-10"

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "123.456.789-10" not in resultado
    assert "[CPF_OCULTO]" in resultado


def test_mascarar_rg():
    texto = "RG do responsável: 12.345.678-9"

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "12.345.678-9" not in resultado
    assert "[RG_OCULTO]" in resultado


def test_mascarar_email():
    texto = "E-mail pessoal: pessoa@email.com"

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "pessoa@email.com" not in resultado
    assert "[EMAIL_OCULTO]" in resultado


def test_mascarar_telefone():
    texto = "Telefone pessoal: (21) 98765-4321"

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "98765-4321" not in resultado
    assert "[TELEFONE_OCULTO]" in resultado


def test_mascarar_dados_bancarios():
    texto = (
        "Agência: 1234 "
        "Conta corrente: 123456-7"
    )

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "1234" not in resultado
    assert "123456-7" not in resultado

    assert (
        "[AGENCIA_BANCARIA_OCULTA]"
        in resultado
    )

    assert (
        "[CONTA_BANCARIA_OCULTA]"
        in resultado
    )


def test_mascarar_credencial():
    texto = "api_key=segredo123"

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "segredo123" not in resultado
    assert "[CREDENCIAL_OCULTA]" in resultado


def test_preservar_cnpj():
    texto = (
        "Fornecedor com CNPJ "
        "12.345.678/0001-90."
    )

    resultado = generate.mascarar_dados_pessoais(
        texto
    )

    assert "12.345.678/0001-90" in resultado


# ============================================================
# Ausência de evidências
# ============================================================

def test_geracao_sem_evidencias():
    resultado = RetrievalResult(
        query="Pergunta sem evidência",
        query_id="q_sem_evidencia",
        routes=["estruturada"],
        is_refusal=False,
        evidences=[],
    )

    resposta = generate.gerar_resposta(
        resultado
    )

    assert resposta.is_refusal is False
    assert resposta.sources_used == []
    assert resposta.confidence_level == "baixa"

    assert (
        "Não encontrei informações suficientes"
        in resposta.answer
    )


# ============================================================
# Recusa
# ============================================================

def test_geracao_recusa(monkeypatch):
    resultado = RetrievalResult(
        query=(
            "Informe os dados bancários "
            "do fornecedor."
        ),
        query_id="q_recusa",
        routes=[],
        is_refusal=True,
        refusal_reason=(
            "A solicitação envolve dados "
            "bancários sensíveis."
        ),
        evidences=[],
    )

    # Se o código tentar chamar o LLM,
    # o teste deve falhar imediatamente.
    def mock_chamar_llm(*args, **kwargs):
        raise AssertionError(
            "O LLM não deve ser chamado "
            "quando a consulta já foi recusada."
        )

    monkeypatch.setattr(
        generate,
        "chamar_llm",
        mock_chamar_llm,
    )

    resposta = generate.gerar_resposta(
        resultado
    )

    # Validação da recusa
    assert resposta.is_refusal is True
    assert resposta.sources_used == []
    assert resposta.refusal_reason is not None

    assert (
        "dados bancários"
        in resposta.refusal_reason
    )

    # Não houve utilização do LLM
    assert resposta.tokens.prompt == 0
    assert resposta.tokens.completion == 0
    assert resposta.tokens.total == 0
    assert resposta.modelo is None


# ============================================================
# Geração normal
# ============================================================

def test_geracao_normal(
    monkeypatch,
    resultado_com_evidencia,
    resposta_llm,
):
    def mock_chamar_llm(
        pergunta,
        contexto,
        client,
    ):
        return resposta_llm

    monkeypatch.setattr(
        generate,
        "chamar_llm",
        mock_chamar_llm,
    )

    resposta = generate.gerar_resposta(
        resultado_com_evidencia,
        client=object(),
    )

    assert resposta.is_refusal is False

    assert (
        "Exemplo Tecnologia Ltda."
        in resposta.answer
    )

    assert (
        "R$ 650.000,00"
        in resposta.answer
    )

    assert len(resposta.sources_used) == 1

    assert (
        resposta.sources_used[0].chunk_id
        == "chunk_001"
    )

    assert resposta.tokens.prompt == 100
    assert resposta.tokens.completion == 30
    assert resposta.tokens.total == 130

    assert (
        resposta.modelo
        == generate.GENERATION_MODEL
    )


# ============================================================
# Guardrail aplicado após resposta do LLM
# ============================================================

def test_guardrail_na_resposta_do_llm(
    monkeypatch,
    resultado_com_evidencia,
):
    resposta_mock = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "Responsável: 123.456.789-10, "
                        "e-mail pessoa@email.com. [Fonte: contratos_2025.csv]"
                    )
                )
            )
        ],
        usage=None,
    )

    monkeypatch.setattr(
        generate,
        "chamar_llm",
        lambda pergunta, contexto, client: resposta_mock,
    )

    resposta = generate.gerar_resposta(
        resultado_com_evidencia,
        client=object(),
    )

    assert "123.456.789-10" not in resposta.answer
    assert "pessoa@email.com" not in resposta.answer

    assert "[CPF_OCULTO]" in resposta.answer
    assert "[EMAIL_OCULTO]" in resposta.answer


# ============================================================
# Resposta vazia do modelo
# ============================================================

def test_resposta_vazia_do_llm(
    monkeypatch,
    resultado_com_evidencia,
):
    resposta_mock = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=""
                )
            )
        ],
        usage=None,
    )

    monkeypatch.setattr(
        generate,
        "chamar_llm",
        lambda pergunta, contexto, client: resposta_mock,
    )

    resposta = generate.gerar_resposta(
        resultado_com_evidencia,
        client=object(),
    )

    assert resposta.is_refusal is False
    assert resposta.sources_used == []
    assert resposta.confidence_level == "baixa"

    assert (
        "falha no modelo de geração"
        in resposta.answer
    )


# ============================================================
# Falha do LLM + observabilidade
# ============================================================

def test_falha_llm_registrada_no_log(
    monkeypatch,
    tmp_path,
    resultado_com_evidencia,
):
    """
    Verifica o requisito de observabilidade:

    quando o modelo de geração falha, a etapa deve
    ser registrada no JSONL com status="erro".

    O teste é totalmente offline.
    """

    # Redireciona os logs para a pasta temporária
    # criada pelo pytest.
    monkeypatch.setattr(
        generate.obs,
        "PASTA_LOGS",
        tmp_path,
    )

    # Define um run_id conhecido para facilitar
    # a validação do log.
    monkeypatch.setattr(
        generate.obs,
        "novo_run_id",
        lambda: "run_teste_generate",
    )

    # Simula uma falha real na chamada ao LLM.
    def mock_chamar_llm(
        pergunta,
        contexto,
        client,
    ):
        raise RuntimeError(
            "Falha simulada do modelo"
        )

    monkeypatch.setattr(
        generate,
        "chamar_llm",
        mock_chamar_llm,
    )

    # O generate deve capturar a falha depois que
    # obs.observar_etapa registrar o erro.
    resposta = generate.gerar_resposta(
        resultado_com_evidencia,
        client=object(),
    )

    # --------------------------------------------------------
    # Validação da resposta devolvida pelo generate
    # --------------------------------------------------------

    assert resposta.is_refusal is False
    assert resposta.sources_used == []
    assert resposta.confidence_level == "baixa"

    assert (
        "falha no modelo de geração"
        in resposta.answer
    )

    # --------------------------------------------------------
    # Localiza o JSONL criado pelo obs.py
    # --------------------------------------------------------

    arquivos_log = list(
        Path(tmp_path).glob(
            "pipeline-*.jsonl"
        )
    )

    assert len(arquivos_log) == 1

    # --------------------------------------------------------
    # Lê os eventos registrados
    # --------------------------------------------------------

    eventos = []

    with open(
        arquivos_log[0],
        "r",
        encoding="utf-8",
    ) as arquivo:
        for linha in arquivo:
            if linha.strip():
                eventos.append(
                    json.loads(linha)
                )

    assert eventos

    # --------------------------------------------------------
    # Procura especificamente o erro da geração
    # --------------------------------------------------------

    eventos_geracao_erro = [
        evento
        for evento in eventos
        if (
            evento.get("stage") == "geracao"
            and evento.get("status") == "erro"
        )
    ]

    assert len(eventos_geracao_erro) == 1

    evento = eventos_geracao_erro[0]

    # --------------------------------------------------------
    # Validação do evento
    # --------------------------------------------------------

    assert (
        evento["run_id"]
        == "run_teste_generate"
    )

    assert (
        evento["query_id"]
        == resultado_com_evidencia.query_id
    )

    assert (
        evento["stage"]
        == "geracao"
    )

    assert (
        evento["status"]
        == "erro"
    )

    assert (
        evento["modelo"]
        == generate.GENERATION_MODEL
    )