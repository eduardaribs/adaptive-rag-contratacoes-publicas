"""
teste_retrieve.py

Testes unitários/offline para src/retrieve.py.

Objetivos:
- validar tokenização e conversão numérica;
- validar natureza, rotas e filtros;
- validar busca densa e BM25 com objetos falsos;
- validar filtragem e fusão RRF;
- validar o fluxo de recuperar_evidencias sem rede e sem artefatos reais.

O retrieve.py original NÃO é alterado.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


import src.retrieve as retrieve


# ============================================================
# OBJETOS FALSOS
# ============================================================

class FakeEmbeddings:
    def create(self, input, model):
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[1.0, 0.0, 0.0]
                )
            ]
        )


class FakeClient:
    def __init__(self):
        self.embeddings = FakeEmbeddings()


class FakeFaiss:
    def __init__(self, distancias=None, posicoes=None, ntotal=3):
        self.ntotal = ntotal
        self._distancias = np.array(
            [distancias or [0.10, 0.20, 0.30]],
            dtype="float32",
        )
        self._posicoes = np.array(
            [posicoes or [0, 1, 2]],
            dtype="int64",
        )

    def search(self, vetor, quantidade):
        return (
            self._distancias[:, :quantidade],
            self._posicoes[:, :quantidade],
        )


class FakeBM25:
    def __init__(self, scores):
        self.scores = np.array(scores, dtype=float)
        self.tokens_recebidos = None

    def get_scores(self, tokens):
        self.tokens_recebidos = tokens
        return self.scores


# ============================================================
# FIXTURES AUXILIARES
# ============================================================

@pytest.fixture
def chunks_teste():
    return [
        {
            "chunk_id": "chunk_1",
            "text": "Contrato de tecnologia no RJ em 2025.",
            "metadata": {
                "uf": "RJ",
                "ano": 2025,
                "valor": 650000,
                "modalidade": "Pregão Eletrônico",
                "municipio": "Rio de Janeiro",
                "fornecedor": "Empresa Tecnologia Ltda.",
                "sensitivity": "publico",
                "natureza": "estruturada",
                "base_id": "estruturada_pncp_rj",
                "source_file": "contratos_2025.json",
                "doc_type": "contratacao",
            },
        },
        {
            "chunk_id": "chunk_2",
            "text": "Contrato municipal de alimentação.",
            "metadata": {
                "uf": "RJ",
                "ano": 2025,
                "valor": 300000,
                "modalidade": "Pregão Eletrônico",
                "municipio": "Niterói",
                "fornecedor": "Alimentos Exemplo Ltda.",
                "sensitivity": "publico",
                "natureza": "estruturada",
                "base_id": "estruturada_pncp_rj",
                "source_file": "contratos_2025.json",
                "doc_type": "contratacao",
            },
        },
        {
            "chunk_id": "chunk_3",
            "text": "Informação restrita para teste.",
            "metadata": {
                "uf": "RJ",
                "ano": 2025,
                "valor": 900000,
                "sensitivity": "restrito",
                "natureza": "estruturada",
                "base_id": "estruturada_pncp_rj",
                "source_file": "restrito.json",
                "doc_type": "contratacao",
            },
        },
    ]


# ============================================================
# TOKENIZAÇÃO E CONVERSÃO
# ============================================================

def test_tokenizar():
    tokens = retrieve.tokenizar(
        "Contratos de Tecnologia no RJ em 2025!"
    )

    assert tokens == [
        "contratos",
        "de",
        "tecnologia",
        "no",
        "rj",
        "em",
        "2025",
    ]


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        (500000, 500000.0),
        (500000.50, 500000.50),
        ("R$ 500.000,00", 500000.0),
        ("750000", 750000.0),
        (None, None),
        ("valor inválido", None),
    ],
)
def test_converter_numero(entrada, esperado):
    assert retrieve._converter_numero(entrada) == esperado


# ============================================================
# NATUREZA / ROTAS
# ============================================================

def test_identificar_natureza_por_metadata():
    chunk = {
        "metadata": {
            "natureza": "estruturada",
        }
    }

    assert retrieve.identificar_natureza(chunk) == "estruturada"


def test_identificar_natureza_por_base_id():
    chunk = {
        "metadata": {
            "base_id": "base_normativa_lei_14133",
        }
    }

    assert retrieve.identificar_natureza(chunk) == "normativa"


def test_identificar_natureza_desconhecida():
    chunk = {
        "metadata": {
            "base_id": "base_sem_classificacao",
        }
    }

    assert retrieve.identificar_natureza(chunk) is None


def test_chunk_atende_rota():
    chunk = {
        "metadata": {
            "natureza": "estruturada",
        }
    }

    assert retrieve.chunk_atende_rotas(
        chunk,
        ["estruturada"],
    ) is True

    assert retrieve.chunk_atende_rotas(
        chunk,
        ["normativa"],
    ) is False


def test_chunk_sem_natureza_continua_elegivel():
    chunk = {"metadata": {}}

    assert retrieve.chunk_atende_rotas(
        chunk,
        ["estruturada"],
    ) is True


# ============================================================
# FILTROS
# ============================================================

def test_chunk_publico_atende_filtros(chunks_teste):
    filtros = {
        "uf": "RJ",
        "ano": 2025,
        "valor_minimo": 500000,
        "modalidade": "Pregão",
        "municipio": "Rio de Janeiro",
        "fornecedor": "Tecnologia",
    }

    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        filtros,
    ) is True


def test_chunk_restrito_nao_atende_filtros(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[2],
        {},
    ) is False


def test_filtro_uf(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        {"uf": "SP"},
    ) is False


def test_filtro_ano(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        {"ano": 2024},
    ) is False


def test_filtro_valor_minimo(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        {"valor_minimo": 700000},
    ) is False


def test_filtro_valor_maximo(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        {"valor_maximo": 600000},
    ) is False


def test_filtro_textual_case_insensitive(chunks_teste):
    assert retrieve.chunk_atende_filtros(
        chunks_teste[0],
        {
            "modalidade": "pregão",
            "fornecedor": "tecnologia",
        },
    ) is True


# ============================================================
# EMBEDDING / BUSCA DENSA
# ============================================================

def test_gerar_embedding_consulta():
    client = FakeClient()

    vetor = retrieve.gerar_embedding_consulta(
        "contratos de tecnologia",
        client,
    )

    assert isinstance(vetor, np.ndarray)
    assert vetor.dtype == np.float32
    assert vetor.shape == (1, 3)


def test_busca_densa():
    client = FakeClient()
    indice = FakeFaiss()
    ids = ["chunk_1", "chunk_2", "chunk_3"]

    resultados = retrieve.busca_densa(
        pergunta="tecnologia",
        client=client,
        indice_faiss=indice,
        ids=ids,
        fetch_k=2,
    )

    assert len(resultados) == 2
    assert resultados[0]["chunk_id"] == "chunk_1"
    assert resultados[1]["chunk_id"] == "chunk_2"
    assert "dense_distance" in resultados[0]


def test_busca_densa_ignora_posicao_invalida():
    client = FakeClient()
    indice = FakeFaiss(
        distancias=[0.1, 0.2, 0.3],
        posicoes=[0, -1, 99],
        ntotal=3,
    )
    ids = ["chunk_1", "chunk_2", "chunk_3"]

    resultados = retrieve.busca_densa(
        pergunta="teste",
        client=client,
        indice_faiss=indice,
        ids=ids,
        fetch_k=3,
    )

    assert len(resultados) == 1
    assert resultados[0]["chunk_id"] == "chunk_1"


# ============================================================
# BM25
# ============================================================

def test_busca_bm25():
    indice = FakeBM25(
        scores=[0.5, 2.0, 1.0]
    )
    ids = ["chunk_1", "chunk_2", "chunk_3"]

    resultados = retrieve.busca_bm25(
        pergunta="contrato tecnologia",
        indice_bm25=indice,
        ids=ids,
        fetch_k=2,
    )

    assert len(resultados) == 2
    assert resultados[0]["chunk_id"] == "chunk_2"
    assert resultados[1]["chunk_id"] == "chunk_3"
    assert indice.tokens_recebidos == [
        "contrato",
        "tecnologia",
    ]


# ============================================================
# FILTRAGEM DE RESULTADOS
# ============================================================

def test_filtrar_resultados(chunks_teste):
    chunks_por_id = {
        chunk["chunk_id"]: chunk
        for chunk in chunks_teste
    }

    resultados = [
        {"chunk_id": "chunk_1"},
        {"chunk_id": "chunk_2"},
        {"chunk_id": "chunk_3"},
        {"chunk_id": "inexistente"},
    ]

    filtrados = retrieve.filtrar_resultados(
        resultados=resultados,
        chunks_por_id=chunks_por_id,
        rotas=["estruturada"],
        filtros={
            "uf": "RJ",
            "ano": 2025,
            "valor_minimo": 500000,
        },
    )

    assert [item["chunk_id"] for item in filtrados] == [
        "chunk_1"
    ]


# ============================================================
# RRF
# ============================================================

def test_fusao_rrf_prioriza_item_presente_nas_duas_buscas():
    densos = [
        {
            "chunk_id": "chunk_1",
            "dense_distance": 0.1,
        },
        {
            "chunk_id": "chunk_2",
            "dense_distance": 0.2,
        },
    ]

    bm25 = [
        {
            "chunk_id": "chunk_2",
            "bm25_score": 5.0,
        },
        {
            "chunk_id": "chunk_3",
            "bm25_score": 4.0,
        },
    ]

    ranking = retrieve.fusao_rrf(
        resultados_densos=densos,
        resultados_bm25=bm25,
        k_rrf=60,
    )

    assert ranking[0]["chunk_id"] == "chunk_2"
    assert ranking[0]["retrieval_sources"] == [
        "bm25",
        "dense",
    ]
    assert ranking[0]["dense_distance"] == 0.2
    assert ranking[0]["bm25_score"] == 5.0


def test_fusao_rrf_sem_resultados():
    assert retrieve.fusao_rrf([], []) == []


# ============================================================
# FLUXO COMPLETO OFFLINE
# ============================================================

def test_recuperar_evidencias_recusa_sem_carregar_indices(monkeypatch):
    analise = {
        "query": "dados bancários",
        "query_id": "q_teste",
        "routes": [],
        "filters": {},
        "is_refusal": True,
        "refusal_reason": "Solicitação de dado sensível.",
        "justification": "Consulta não permitida.",
        "router_fallback": False,
    }

    monkeypatch.setattr(
        retrieve,
        "analisar_consulta",
        lambda pergunta, client, run_id=None: analise,
    )

    def nao_deve_carregar():
        raise AssertionError(
            "carregar_artefatos não deveria ser chamado em recusa."
        )

    monkeypatch.setattr(
        retrieve,
        "carregar_artefatos",
        nao_deve_carregar,
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta="Informe dados bancários do fornecedor.",
        client=FakeClient(),
    )

    assert resultado["is_refusal"] is True
    assert resultado["evidences"] == []
    assert resultado["refusal_reason"] == (
        "Solicitação de dado sensível."
    )
    assert resultado["stage"] == "fusao_rrf"


def test_recuperar_evidencias_fluxo_normal(monkeypatch, chunks_teste):
    chunks_por_id = {
        chunk["chunk_id"]: chunk
        for chunk in chunks_teste
    }

    ids = ["chunk_1", "chunk_2", "chunk_3"]

    analise = {
        "query": "contratos tecnologia",
        "query_id": "q_fluxo",
        "routes": ["estruturada"],
        "filters": {
            "uf": "RJ",
            "ano": 2025,
            "valor_minimo": 500000,
        },
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Consulta sobre dados estruturados.",
        "router_fallback": False,
    }

    monkeypatch.setattr(
        retrieve,
        "analisar_consulta",
        lambda pergunta, client, run_id=None: analise,
    )

    monkeypatch.setattr(
        retrieve,
        "carregar_artefatos",
        lambda: (
            chunks_teste,
            chunks_por_id,
            ids,
            object(),
            object(),
        ),
    )

    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "dense_distance": 0.10,
            },
            {
                "chunk_id": "chunk_2",
                "dense_distance": 0.20,
            },
            {
                "chunk_id": "chunk_3",
                "dense_distance": 0.30,
            },
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "bm25_score": 4.0,
            },
            {
                "chunk_id": "chunk_2",
                "bm25_score": 3.0,
            },
            {
                "chunk_id": "chunk_3",
                "bm25_score": 2.0,
            },
        ],
    )

    import src.retrieval_lexical as lexical

    def buscar_contexto_simulado(
        pergunta,
        candidatos,
        chunks_por_id,
        identificar_natureza,
        fetch_k=50,
    ):
        # Os filtros devem ser aplicados antes da busca contextual.
        assert [
            item["chunk_id"] for item in candidatos
        ] == ["chunk_1"]
        assert fetch_k == 10

        return [{
            "chunk_id": "chunk_1",
            "bm25_score": 4.0,
        }]

    monkeypatch.setattr(
        lexical,
        "buscar_contexto",
        buscar_contexto_simulado,
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta="Quais contratos de tecnologia "
        "no RJ em 2025 acima de R$ 500 mil?",
        top_k=5,
        fetch_k=10,
        client=FakeClient(),
    )

    assert resultado["query_id"] == "q_fluxo"
    assert resultado["routes"] == ["estruturada"]
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False
    assert resultado["stage"] == "fusao_rrf"

    assert len(resultado["evidences"]) == 1

    evidencia = resultado["evidences"][0]

    assert evidencia["chunk_id"] == "chunk_1"
    assert evidencia["source_file"] == "contratos_2025.json"
    assert evidencia["doc_type"] == "contratacao"
    assert evidencia["sensitivity"] == "publico"
    assert evidencia["natureza"] == "estruturada"
    assert evidencia["retrieval_sources"] == [
        "bm25",
        "dense",
    ]

    resumo = resultado["retrieval_summary"]

    assert resumo["dense_candidates"] == 1
    assert resumo["bm25_candidates"] == 1
    assert resumo["rrf_candidates"] == 1
    assert resumo["returned"] == 1


def test_recuperar_evidencias_respeita_top_k(monkeypatch, chunks_teste):
    chunks_publicos = chunks_teste[:2]

    chunks_por_id = {
        chunk["chunk_id"]: chunk
        for chunk in chunks_publicos
    }

    ids = ["chunk_1", "chunk_2"]

    analise = {
        "query": "contratos",
        "query_id": "q_top_k",
        "routes": ["estruturada"],
        "filters": {
            "uf": "RJ",
            "ano": 2025,
        },
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Consulta estruturada.",
        "router_fallback": False,
    }

    monkeypatch.setattr(
        retrieve,
        "analisar_consulta",
        lambda pergunta, client, run_id=None: analise,
    )

    monkeypatch.setattr(
        retrieve,
        "carregar_artefatos",
        lambda: (
            chunks_publicos,
            chunks_por_id,
            ids,
            object(),
            object(),
        ),
    )

    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "dense_distance": 0.1,
            },
            {
                "chunk_id": "chunk_2",
                "dense_distance": 0.2,
            },
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "bm25_score": 2.0,
            },
            {
                "chunk_id": "chunk_2",
                "bm25_score": 1.0,
            },
        ],
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta="Quais contratos existem?",
        top_k=1,
        client=FakeClient(),
    )

    assert len(resultado["evidences"]) == 1
    assert resultado["retrieval_summary"]["returned"] == 1
