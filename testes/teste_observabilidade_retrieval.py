"""
teste_observabilidade_retrieval.py

Testes offline da observabilidade das etapas de recuperação.

Objetivos:
- validar eventos separados para Dense e BM25;
- validar campos obrigatórios dos eventos;
- preservar run_id e query_id;
- validar buscas sem resultados;
- validar falha controlada no BM25;
- garantir que o conteúdo das evidências não seja exposto nos logs.

Este arquivo não altera src/retrieve.py.
"""

import json

import pytest

from src import obs
import src.retrieve as retrieve


class FakeClient:
    """Cliente mínimo para execução offline."""

    pass


def ler_eventos(tmp_path):
    """Lê todos os eventos JSONL produzidos durante o teste."""

    arquivos = list(tmp_path.glob("pipeline-*.jsonl"))

    assert len(arquivos) == 1

    eventos = []

    with arquivos[0].open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        for linha in arquivo:
            eventos.append(json.loads(linha))

    return eventos


def buscar_evento(eventos, stage):
    """Retorna o primeiro evento correspondente ao stage."""

    encontrados = [
        evento
        for evento in eventos
        if evento["stage"] == stage
    ]

    assert len(encontrados) == 1

    return encontrados[0]


@pytest.fixture
def ambiente_retrieval(monkeypatch, tmp_path):
    """
    Prepara recuperar_evidencias para funcionar totalmente offline.
    """

    monkeypatch.setattr(
        obs,
        "PASTA_LOGS",
        tmp_path,
    )

    chunks = [
        {
            "chunk_id": "chunk_1",
            "text": (
                "CONTEUDO_SENSIVEL_TESTE "
                "Contrato de tecnologia no RJ."
            ),
            "metadata": {
                "uf": "RJ",
                "ano": 2025,
                "valor": 650000,
                "sensitivity": "publico",
                "natureza": "estruturada",
                "base_id": "estruturada_pncp_rj",
                "source_file": "contratos.json",
                "doc_type": "contratacao",
            },
        },
        {
            "chunk_id": "chunk_2",
            "text": (
                "OUTRO_CONTEUDO_SENSIVEL_TESTE "
                "Outro contrato público."
            ),
            "metadata": {
                "uf": "RJ",
                "ano": 2025,
                "valor": 700000,
                "sensitivity": "publico",
                "natureza": "estruturada",
                "base_id": "estruturada_pncp_rj",
                "source_file": "contratos.json",
                "doc_type": "contratacao",
            },
        },
    ]

    chunks_por_id = {
        chunk["chunk_id"]: chunk
        for chunk in chunks
    }

    ids = [
        "chunk_1",
        "chunk_2",
    ]

    analise = {
        "query": "contratos de tecnologia",
        "query_id": "q_obs_retrieval",
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
            chunks,
            chunks_por_id,
            ids,
            object(),
            object(),
        ),
    )

    return {
        "chunks": chunks,
        "analise": analise,
        "tmp_path": tmp_path,
    }


def test_eventos_dense_e_bm25_sao_registrados(
    monkeypatch,
    ambiente_retrieval,
):
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
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "bm25_score": 3.0,
            },
            {
                "chunk_id": "chunk_2",
                "bm25_score": 2.0,
            },
        ],
    )

    retrieve.recuperar_evidencias(
        pergunta="Quais contratos de tecnologia existem?",
        client=FakeClient(),
        run_id="run_obs_retrieval",
    )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    stages = [
        evento["stage"]
        for evento in eventos
    ]

    assert "retrieval_denso" in stages
    assert "retrieval_bm25" in stages


def test_eventos_retrieval_possuem_campos_obrigatorios(
    monkeypatch,
    ambiente_retrieval,
):
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "dense_distance": 0.10,
            },
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "bm25_score": 3.0,
            },
        ],
    )

    monkeypatch.setattr(__import__('src.retrieval_lexical', fromlist=['buscar_contexto']), 'buscar_contexto', lambda **kwargs: [{'chunk_id': 'chunk_1', 'bm25_score': 3.0}])

    retrieve.recuperar_evidencias(
        pergunta="Contratos de tecnologia",
        client=FakeClient(),
        run_id="run_campos",
    )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    for stage in (
        "retrieval_denso",
        "retrieval_bm25",
    ):
        evento = buscar_evento(
            eventos,
            stage,
        )

        assert "ts" in evento
        assert "run_id" in evento
        assert "query_id" in evento
        assert "stage" in evento
        assert "status" in evento
        assert "latencia_ms" in evento
        assert "input" in evento
        assert "output" in evento

        assert evento["status"] == "ok"

        assert (
            evento["output"]["candidatos"]
            == 1
        )


def test_run_id_e_query_id_sao_preservados(
    monkeypatch,
    ambiente_retrieval,
):
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [],
    )

    run_id = "run_consistencia"

    retrieve.recuperar_evidencias(
        pergunta="Consulta sem resultados",
        client=FakeClient(),
        run_id=run_id,
    )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    dense = buscar_evento(
        eventos,
        "retrieval_denso",
    )

    bm25 = buscar_evento(
        eventos,
        "retrieval_bm25",
    )

    assert dense["run_id"] == run_id
    assert bm25["run_id"] == run_id

    assert (
        dense["query_id"]
        == "q_obs_retrieval"
    )

    assert (
        bm25["query_id"]
        == "q_obs_retrieval"
    )

    assert (
        dense["query_id"]
        == bm25["query_id"]
    )


def test_retrieval_sem_resultados_e_registrado(
    monkeypatch,
    ambiente_retrieval,
):
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [],
    )

    resultado = retrieve.recuperar_evidencias(
        pergunta="Consulta sem correspondência",
        client=FakeClient(),
        run_id="run_sem_resultados",
    )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    dense = buscar_evento(
        eventos,
        "retrieval_denso",
    )

    bm25 = buscar_evento(
        eventos,
        "retrieval_bm25",
    )

    assert dense["status"] == "ok"
    assert bm25["status"] == "ok"

    assert (
        dense["output"]["candidatos"]
        == 0
    )

    assert (
        bm25["output"]["candidatos"]
        == 0
    )

    assert resultado["evidences"] == []


def test_falha_controlada_bm25_e_registrada(
    monkeypatch,
    ambiente_retrieval,
):
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "dense_distance": 0.10,
            },
        ],
    )

    def busca_bm25_com_erro(**kwargs):
        raise RuntimeError(
            "Falha simulada BM25"
        )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        busca_bm25_com_erro,
    )

    monkeypatch.setattr(__import__('src.retrieval_lexical', fromlist=['buscar_contexto']), 'buscar_contexto', busca_bm25_com_erro)

    with pytest.raises(
        RuntimeError,
        match="Falha simulada BM25",
    ):
        retrieve.recuperar_evidencias(
            pergunta="Consulta com falha BM25",
            client=FakeClient(),
            run_id="run_falha_bm25",
        )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    dense = buscar_evento(
        eventos,
        "retrieval_denso",
    )

    bm25 = buscar_evento(
        eventos,
        "retrieval_bm25",
    )

    assert dense["status"] == "ok"
    assert bm25["status"] == "erro"

    assert (
        bm25["output"]["erro"]
        == "RuntimeError"
    )

    assert (
        bm25["output"]["mensagem"]
        == "Falha simulada BM25"
    )


def test_logs_nao_expoem_conteudo_das_evidencias(
    monkeypatch,
    ambiente_retrieval,
):
    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "dense_distance": 0.10,
            },
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {
                "chunk_id": "chunk_1",
                "bm25_score": 3.0,
            },
        ],
    )

    retrieve.recuperar_evidencias(
        pergunta="Contratos de tecnologia",
        client=FakeClient(),
        run_id="run_privacidade",
    )

    eventos = ler_eventos(
        ambiente_retrieval["tmp_path"]
    )

    eventos_retrieval = [
        evento
        for evento in eventos
        if evento["stage"] in {
            "retrieval_denso",
            "retrieval_bm25",
        }
    ]

    serializado = json.dumps(
        eventos_retrieval,
        ensure_ascii=False,
    )

    assert (
        "CONTEUDO_SENSIVEL_TESTE"
        not in serializado
    )

    assert (
        "OUTRO_CONTEUDO_SENSIVEL_TESTE"
        not in serializado
    )

def test_eventos_retrieval_registram_rotas_filtros_ids_e_bases(
    monkeypatch,
    ambiente_retrieval,
):
    """Valida os novos campos dos eventos Dense e BM25."""

    monkeypatch.setattr(
        retrieve,
        "busca_densa",
        lambda **kwargs: [
            {"chunk_id": "chunk_1", "dense_distance": 0.10},
            {"chunk_id": "chunk_2", "dense_distance": 0.20},
        ],
    )

    monkeypatch.setattr(
        retrieve,
        "busca_bm25",
        lambda **kwargs: [
            {"chunk_id": "chunk_2", "bm25_score": 3.0},
            {"chunk_id": "chunk_1", "bm25_score": 2.0},
        ],
    )

    monkeypatch.setattr(__import__('src.retrieval_lexical', fromlist=['buscar_contexto']), 'buscar_contexto', lambda **kwargs: [{'chunk_id': 'chunk_2', 'bm25_score': 3.0}, {'chunk_id': 'chunk_1', 'bm25_score': 2.0}])

    retrieve.recuperar_evidencias(
        pergunta="Quais contratos de tecnologia existem no RJ em 2025?",
        client=FakeClient(),
        run_id="run_campos_observabilidade",
    )

    eventos = ler_eventos(ambiente_retrieval["tmp_path"])
    dense = buscar_evento(eventos, "retrieval_denso")
    bm25 = buscar_evento(eventos, "retrieval_bm25")

    filtros_esperados = {
        "uf": "RJ",
        "ano": 2025,
    }

    assert dense["output"]["routes"] == ["estruturada"]
    assert dense["output"]["filters"] == filtros_esperados
    assert dense["output"]["candidatos"] == 2
    assert dense["output"]["top_chunk_ids"] == [
        "chunk_1",
        "chunk_2",
    ]
    assert dense["output"]["bases"] == [
        "estruturada_pncp_rj"
    ]

    assert bm25["output"]["routes"] == ["estruturada"]
    assert bm25["output"]["filters"] == filtros_esperados
    assert bm25["output"]["candidatos"] == 2
    assert bm25["output"]["top_chunk_ids"] == [
        "chunk_2",
        "chunk_1",
    ]
    assert bm25["output"]["bases"] == [
        "estruturada_pncp_rj"
    ]

    serializado = json.dumps(
        [dense, bm25],
        ensure_ascii=False,
    )

    assert "CONTEUDO_SENSIVEL_TESTE" not in serializado
    assert "OUTRO_CONTEUDO_SENSIVEL_TESTE" not in serializado