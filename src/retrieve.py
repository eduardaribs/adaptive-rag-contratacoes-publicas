import json
import os
import pickle
import re
import time
from typing import Any, Dict, List, Optional, Set

import faiss
import numpy as np
from openai import OpenAI

from src.router import OLLAMA_URL, analisar_consulta

# Importação do novo módulo de rerank e documentação de configuração (02/10)
# Para ativar o rerank futuramente, definir RERANK_ENABLED=true no .env
# Variáveis preparadas: RERANK_URL, RERANK_AUTH, RERANK_MODEL, RERANK_TIMEOUT
try:
    from . import obs, rerank
    from .schema import RetrievalResult
except ImportError:  # permite "python src/retrieve.py" direto, sem pacote.
    import obs
    import rerank
    from schema import RetrievalResult


EMBEDDING_MODEL = "xagi/qwen3-embedding:0.6b-q4_k_m"

CAMINHO_CHUNKS = "data/processed/chunks_teste.json"
CAMINHO_FAISS = "data/indices/faiss_index.bin"
CAMINHO_BM25 = "data/indices/bm25_index.pkl"
CAMINHO_IDS = "data/indices/chunk_ids.json"

ROTAS_VALIDAS = {
    "normativa",
    "estruturada",
    "conversacional",
    "agregada",
}


def tokenizar(texto: str) -> List[str]:
    """
    Tokenização simples para consultas BM25 em português.
    """
    return re.findall(
        r"\b[\wÀ-ÿ]+\b",
        texto.lower(),
        flags=re.UNICODE,
    )


def carregar_artefatos(
    caminho_chunks: str = CAMINHO_CHUNKS,
    caminho_faiss: str = CAMINHO_FAISS,
    caminho_bm25: str = CAMINHO_BM25,
    caminho_ids: str = CAMINHO_IDS,
):
    """
    Carrega chunks e índices já persistidos.
    Não refaz a indexação.
    """
    caminhos = [
        caminho_chunks,
        caminho_faiss,
        caminho_bm25,
        caminho_ids,
    ]

    faltando = [caminho for caminho in caminhos if not os.path.exists(caminho)]

    if faltando:
        raise FileNotFoundError(
            "Artefatos não encontrados: "
            + ", ".join(faltando)
            + ". Execute primeiro ingest.py e index.py."
        )

    with open(caminho_chunks, "r", encoding="utf-8") as arquivo:
        chunks = json.load(arquivo)

    with open(caminho_ids, "r", encoding="utf-8") as arquivo:
        ids = json.load(arquivo)

    indice_faiss = faiss.read_index(caminho_faiss)

    # O pickle deve ser carregado somente de arquivo criado pela própria equipe.
    with open(caminho_bm25, "rb") as arquivo:
        indice_bm25 = pickle.load(arquivo)

    if len(ids) != len(chunks):
        raise ValueError(
            f"Inconsistência: {len(ids)} IDs e {len(chunks)} chunks."
        )

    if indice_faiss.ntotal != len(ids):
        raise ValueError(
            f"Inconsistência: FAISS possui {indice_faiss.ntotal} vetores, "
            f"mas existem {len(ids)} IDs."
        )

    chunks_por_id = {}

    for chunk in chunks:
        chunk_id = (
            chunk.get("metadata", {}).get("chunk_id")
            or chunk.get("chunk_id")
        )

        if not chunk_id:
            raise ValueError(
                "Chunk sem chunk_id no nível principal ou em metadata."
            )

        chunks_por_id[chunk_id] = chunk

    return chunks, chunks_por_id, ids, indice_faiss, indice_bm25


def identificar_natureza(chunk: Dict[str, Any]) -> Optional[str]:
    """
    Descobre a natureza pelo metadado ou pelo nome da base.
    """
    metadata = chunk.get("metadata", {})

    natureza = str(metadata.get("natureza", "")).lower().strip()

    if natureza in ROTAS_VALIDAS:
        return natureza

    base_id = str(metadata.get("base_id", "")).lower()

    for rota in ROTAS_VALIDAS:
        if rota in base_id:
            return rota

    return None


def _converter_numero(valor: Any) -> Optional[float]:
    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


def chunk_atende_rotas(
    chunk: Dict[str, Any],
    rotas: List[str],
    exigir_natureza: bool = False,
) -> bool:
    if not rotas:
        return True

    natureza = identificar_natureza(chunk)

    if natureza is None:
        return not exigir_natureza

    return natureza in rotas


def _sanitizar_texto_evidencia(
    texto: str,
    sensitivity: str,
) -> tuple[str, str]:
    """Mascara dados pessoais antes de expor evidências restritas."""
    sensibilidade = str(sensitivity or "publico").lower().strip()

    if sensibilidade in {"publico", "público"}:
        return texto, "publico"

    if sensibilidade == "restrito":
        try:
            from .generate import mascarar_dados_pessoais
        except ImportError:
            from generate import mascarar_dados_pessoais

        return (
            mascarar_dados_pessoais(texto),
            "restrito_sanitizado",
        )

    return "", "bloqueado"


def chunk_atende_filtros(
    chunk: Dict[str, Any],
    filtros: Dict[str, Any],
) -> bool:
    metadata = chunk.get("metadata", {})

    sensitivity = str(
        metadata.get("sensitivity", "publico")
    ).lower()

    if sensitivity not in {"publico", "público"}:
        restrito_conversacional = (
            sensitivity == "restrito"
            and identificar_natureza(chunk) == "conversacional"
        )

        if not restrito_conversacional:
            return False

    uf = filtros.get("uf")

    if uf and metadata.get("uf"):
        if str(metadata["uf"]).upper() != str(uf).upper():
            return False

    ano = filtros.get("ano")
    ano_metadata = metadata.get("ano")

    # Ano vazio equivale a metadado ausente.
    # A recuperação não confirma o ano de documentos sem esse metadado.
    ano_metadata_ausente = (
        ano_metadata is None
        or (
            isinstance(ano_metadata, str)
            and not ano_metadata.strip()
        )
    )

    if ano and not ano_metadata_ausente:
        try:
            if int(ano_metadata) != int(ano):
                return False
        except (TypeError, ValueError):
            return False

    valor = _converter_numero(
        metadata.get("valor", metadata.get("valor_total"))
    )

    valor_minimo = _converter_numero(filtros.get("valor_minimo"))
    valor_maximo = _converter_numero(filtros.get("valor_maximo"))

    if valor_minimo is not None and valor is not None:
        if valor < valor_minimo:
            return False

    if valor_maximo is not None and valor is not None:
        if valor > valor_maximo:
            return False

    campos_textuais = [
        "modalidade",
        "municipio",
        "fornecedor",
    ]

    for campo in campos_textuais:
        procurado = filtros.get(campo)
        existente = metadata.get(campo)

        if procurado and existente:
            if str(procurado).lower() not in str(existente).lower():
                return False

    return True


def gerar_embedding_consulta(
    pergunta: str,
    client: OpenAI,
) -> np.ndarray:
    resposta = client.embeddings.create(
        input=[pergunta],
        model=EMBEDDING_MODEL,
    )

    vetor = np.array(
        [resposta.data[0].embedding],
        dtype="float32",
    )

    return vetor


def busca_densa(
    pergunta: str,
    client: OpenAI,
    indice_faiss,
    ids: List[str],
    fetch_k: int = 50,
) -> List[Dict[str, Any]]:
    vetor = gerar_embedding_consulta(pergunta, client)

    quantidade = min(fetch_k, indice_faiss.ntotal)

    distancias, posicoes = indice_faiss.search(
        vetor,
        quantidade,
    )

    resultados = []

    for distancia, posicao in zip(distancias[0], posicoes[0]):
        if posicao < 0 or posicao >= len(ids):
            continue

        resultados.append(
            {
                "chunk_id": ids[posicao],
                "dense_distance": float(distancia),
            }
        )

    return resultados


def busca_bm25(
    pergunta: str,
    indice_bm25,
    ids: List[str],
    fetch_k: int = 50,
) -> List[Dict[str, Any]]:
    tokens = tokenizar(pergunta)
    scores = indice_bm25.get_scores(tokens)

    posicoes = np.argsort(scores)[::-1][: min(fetch_k, len(ids))]

    resultados = []

    for posicao in posicoes:
        resultados.append(
            {
                "chunk_id": ids[int(posicao)],
                "bm25_score": float(scores[int(posicao)]),
            }
        )

    return resultados


def filtrar_resultados(
    resultados: List[Dict[str, Any]],
    chunks_por_id: Dict[str, Dict[str, Any]],
    rotas: List[str],
    filtros: Dict[str, Any],
    exigir_natureza: bool = False,
) -> List[Dict[str, Any]]:
    saida = []

    for resultado in resultados:
        chunk = chunks_por_id.get(resultado["chunk_id"])

        if not chunk:
            continue

        if not chunk_atende_rotas(chunk, rotas, exigir_natureza=exigir_natureza):
            continue

        if not chunk_atende_filtros(chunk, filtros):
            continue

        saida.append(resultado)

    return saida


def fusao_rrf(
    resultados_densos: List[Dict[str, Any]],
    resultados_bm25: List[Dict[str, Any]],
    k_rrf: int = 60,
) -> List[Dict[str, Any]]:
    scores: Dict[str, float] = {}
    origens: Dict[str, Set[str]] = {}
    detalhes: Dict[str, Dict[str, Any]] = {}

    for posicao, item in enumerate(resultados_densos, start=1):
        chunk_id = item["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k_rrf + posicao))
        origens.setdefault(chunk_id, set()).add("dense")
        detalhes.setdefault(chunk_id, {}).update(item)

    for posicao, item in enumerate(resultados_bm25, start=1):
        chunk_id = item["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k_rrf + posicao))
        origens.setdefault(chunk_id, set()).add("bm25")
        detalhes.setdefault(chunk_id, {}).update(item)

    ranking = sorted(
        scores.items(),
        key=lambda elemento: elemento[1],
        reverse=True,
    )

    return [
        {
            "chunk_id": chunk_id,
            "rrf_score": score,
            "retrieval_sources": sorted(origens[chunk_id]),
            **detalhes.get(chunk_id, {}),
        }
        for chunk_id, score in ranking
    ]


def _validar_com_retrieval_result(resultado: Dict[str, Any]) -> Dict[str, Any]:
    validado = RetrievalResult(**resultado)
    return validado.model_dump()


def selecionar_resultados_multirrota(
    ranking: List[Dict[str, Any]],
    chunks_por_id: Dict[str, Dict[str, Any]],
    rotas: List[str],
    top_k: int,
) -> List[Dict[str, Any]]:
    if top_k <= 0:
        return []

    if len(rotas) <= 1:
        return ranking[:top_k]

    ids_selecionados = set()

    # Reserva uma evidência por rota
    for rota in rotas:
        if len(ids_selecionados) >= top_k:
            break
        for item in ranking:
            chunk_id = item.get("chunk_id")
            chunk = chunks_por_id.get(chunk_id, {})
            if chunk_id not in ids_selecionados and identificar_natureza(chunk) == rota:
                ids_selecionados.add(chunk_id)
                break

    # Completa vagas
    for item in ranking:
        if len(ids_selecionados) >= top_k:
            break
        chunk_id = item.get("chunk_id")
        if chunk_id not in ids_selecionados:
            ids_selecionados.add(chunk_id)

    # Mantém ordem calculada (agora pode ser a ordem do Rerank)
    return [
        item
        for item in ranking
        if item.get("chunk_id") in ids_selecionados
    ][:top_k]

def recuperar_evidencias(
    pergunta: str,
    top_k: int = 5,
    fetch_k: int = 50,
    client: OpenAI | None = None,
    exigir_natureza: bool = False,
    run_id: str | None = None,
    analise_pronta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    inicio = time.perf_counter()
    run_id = run_id or obs.novo_run_id()

    if client is None:
        import httpx

        client = OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",
            timeout=httpx.Timeout(
                connect=10.0, read=120.0, write=30.0, pool=10.0
            ),
            max_retries=0,
        )

    if analise_pronta is None:
        analise = analisar_consulta(
            pergunta=pergunta,
            client=client,
            run_id=run_id,
        )
    else:
        if not isinstance(analise_pronta, dict):
            raise ValueError("A análise pronta deve ser um dicionário.")

        obrigatorios = {"query_id", "routes", "filters", "is_refusal"}
        if not obrigatorios.issubset(analise_pronta):
            raise ValueError("A análise pronta está incompleta.")

        consulta_original = analise_pronta.get("query")
        if (
            consulta_original is not None
            and consulta_original.strip() != pergunta.strip()
        ):
            raise ValueError("A análise pertence a outra pergunta.")

        analise = dict(analise_pronta)

    query_id = analise["query_id"]

    if analise.get("is_refusal"):
        resultado = {
            "query": pergunta,
            "query_id": query_id,
            "routes": analise["routes"],
            "filters": analise["filters"],
            "is_refusal": True,
            "refusal_reason": analise.get("refusal_reason"),
            "evidences": [],
            "stage": "fusao_rrf",
            "latencia_ms": round((time.perf_counter() - inicio) * 1000, 2),
        }
        return _validar_com_retrieval_result(resultado)

    (
        chunks,
        chunks_por_id,
        ids,
        indice_faiss,
        indice_bm25,
    ) = carregar_artefatos()

    rotas = analise.get("routes", [])
    filtros = analise.get("filters", {})

    from src.document_scope import escopar_documento

    escopo_ata = (
        escopar_documento(pergunta, chunks_por_id, identificar_natureza)
        if "conversacional" in rotas
        else None
    )

    rotas_antes_escopo = list(rotas)
    if (
        escopo_ata is not None
        and re.search(r"\bpncp\b", pergunta, flags=re.IGNORECASE)
        and "estruturada" not in rotas
        and any(
            identificar_natureza(chunks_por_id.get(chunk_id, {}))
            == "estruturada"
            for chunk_id in escopo_ata["ids"]
        )
    ):
        rotas = [*rotas, "estruturada"]

    usar_busca_contextual = (
        escopo_ata is not None
        or (
            bool(rotas)
            and set(rotas).issubset({"estruturada", "normativa"})
        )
    )

    candidatos_contextuais = []
    if usar_busca_contextual:
        candidatos_contextuais = filtrar_resultados(
            [{"chunk_id": identificador} for identificador in ids],
            chunks_por_id,
            rotas,
            filtros,
            exigir_natureza,
        )

    if escopo_ata is not None:
        candidatos_contextuais = [
            item for item in candidatos_contextuais
            if item["chunk_id"] in escopo_ata["ids"]
        ]

        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="validacao",
            input_data={
                "tipo": "escopo_documental",
                "pergunta": pergunta,
            },
        ) as observacao_escopo:
            observacao_escopo["output"] = {
                "fontes": escopo_ata["fontes"],
                "processos": escopo_ata["processos"],
                "motivo": escopo_ata["motivo"],
                "rotas_antes_escopo": rotas_antes_escopo,
                "rotas_apos_escopo": list(rotas),
                "rota_estruturada_complementada": (
                    rotas_antes_escopo != rotas
                ),
                "candidatos_elegiveis": len(candidatos_contextuais),
                "chunk_ids": [
                    item["chunk_id"] for item in candidatos_contextuais
                ],
            }

    with obs.observar_etapa(
        run_id=run_id, query_id=query_id, stage="retrieval_denso", input_data={"pergunta": pergunta, "fetch_k": fetch_k}
    ) as observacao_densa:
        resultados_densos = busca_densa(
            pergunta=pergunta,
            client=client,
            indice_faiss=indice_faiss,
            ids=ids,
            fetch_k=len(ids) if usar_busca_contextual else fetch_k,
        )
        if escopo_ata is not None:
            resultados_densos = [
                item for item in resultados_densos
                if item["chunk_id"] in escopo_ata["ids"]
            ]

        if usar_busca_contextual:
            resultados_densos = filtrar_resultados(
                resultados_densos,
                chunks_por_id,
                rotas,
                filtros,
                exigir_natureza,
            )[:fetch_k]
        top_chunk_ids_denso = [
            item["chunk_id"]
            for item in resultados_densos[:top_k]
            if item.get("chunk_id")
        ]
        bases_densas = sorted({
            chunks_por_id.get(item.get("chunk_id"), {})
            .get("metadata", {})
            .get("base_id")
            for item in resultados_densos
            if item.get("chunk_id")
            and chunks_por_id.get(item.get("chunk_id"), {})
            .get("metadata", {})
            .get("base_id")
        })

        observacao_densa["output"] = {
            "routes": rotas,
            "filters": filtros,
            "candidatos": len(resultados_densos),
            "top_chunk_ids": top_chunk_ids_denso,
            "bases": bases_densas,
        }

    with obs.observar_etapa(
        run_id=run_id, query_id=query_id, stage="retrieval_bm25", input_data={"pergunta": pergunta, "fetch_k": fetch_k}
    ) as observacao_bm25:
        if usar_busca_contextual:
            from src.retrieval_lexical import buscar_contexto

            resultados_bm25 = buscar_contexto(
                pergunta=pergunta,
                candidatos=candidatos_contextuais,
                chunks_por_id=chunks_por_id,
                identificar_natureza=identificar_natureza,
                fetch_k=fetch_k,
            )
        else:
            resultados_bm25 = busca_bm25(
                pergunta=pergunta,
                indice_bm25=indice_bm25,
                ids=ids,
                fetch_k=fetch_k,
            )

        top_chunk_ids_bm25 = [
            item["chunk_id"]
            for item in resultados_bm25[:top_k]
            if item.get("chunk_id")
        ]
        bases_bm25 = sorted({
            chunks_por_id.get(item.get("chunk_id"), {})
            .get("metadata", {})
            .get("base_id")
            for item in resultados_bm25
            if item.get("chunk_id")
            and chunks_por_id.get(item.get("chunk_id"), {})
            .get("metadata", {})
            .get("base_id")
        })

        observacao_bm25["output"] = {
            "routes": rotas,
            "filters": filtros,
            "candidatos": len(resultados_bm25),
            "top_chunk_ids": top_chunk_ids_bm25,
            "bases": bases_bm25,
        }

    with obs.observar_etapa(
        run_id=run_id, query_id=query_id, stage="fusao_rrf", input_data={"routes": rotas, "filters": filtros, "top_k": top_k}
    ) as observacao_fusao:
        resultados_densos = filtrar_resultados(resultados_densos, chunks_por_id, rotas, filtros, exigir_natureza)
        resultados_bm25 = filtrar_resultados(resultados_bm25, chunks_por_id, rotas, filtros, exigir_natureza)

        ranking_rrf = fusao_rrf(resultados_densos, resultados_bm25)

        # --- INTEGRAÇÃO DO RERANK AQUI (02/10) ---
        # Garantir que a estrutura envia dicionários compatíveis para simular a preservação de metadados
        candidatos_para_rerank = []
        for item in ranking_rrf:
            chunk = chunks_por_id.get(item["chunk_id"], {})
            candidatos_para_rerank.append({
                "id": item["chunk_id"],
                "text": chunk.get("text", ""),
                "metadata": chunk.get("metadata", {}),
                "rrf_score_original": item["rrf_score"]
            })

        ranking_reranked_tuples = rerank.executar_rerank(pergunta, candidatos_para_rerank)
        resultado_rerank = rerank.ultimo_resultado()

        # Reconstrói a lista no formato que o selecionar_resultados_multirrota espera
        ranking_final = []
        for doc, novo_score in ranking_reranked_tuples:
            original_item = next((item for item in ranking_rrf if item["chunk_id"] == doc["id"]), {})
            ranking_final.append({
                **original_item,
                "rerank_score": novo_score
            })

        if not ranking_final:
            ranking_final = ranking_rrf
        # ----------------------------------------


        from src.retrieval_method_coverage import cobrir_metodos

        ids_antes_metodos = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]
        cobertura_metodos_habilitada = bool(
            escopo_ata is not None
            and not resultado_rerank.get("applied", False)
            and ranking_final
            and all(
                identificar_natureza(
                    chunks_por_id.get(item["chunk_id"], {})
                ) == "normativa"
                for item in ranking_final
            )
        )
        if cobertura_metodos_habilitada:
            ranking_final = cobrir_metodos(
                ranking_final, resultados_densos,
                resultados_bm25, top_k,
            )
        ids_apos_metodos = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]

        from src.normative_selection import cobrir_definicao

        ids_antes_cobertura = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]
        ranking_final = cobrir_definicao(
            pergunta, ranking_final, chunks_por_id, rotas, top_k,
        )
        ids_apos_cobertura = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]

        from src.factual_selection import cobrir_campos_ata

        ids_antes_campos = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]
        ranking_final = cobrir_campos_ata(
            pergunta, ranking_final, chunks_por_id, rotas, top_k,
            ids_escopo=escopo_ata["ids"] if escopo_ata else None,
        )
        ids_apos_campos = [
            item["chunk_id"] for item in ranking_final[:top_k]
        ]

        ranking_selecionado = selecionar_resultados_multirrota(ranking_final, chunks_por_id, rotas, top_k)

        evidencias = []
        for item in ranking_selecionado:
            chunk = chunks_por_id[item["chunk_id"]]
            metadata = chunk.get("metadata", {})
            sensibilidade_original = metadata.get("sensitivity", "publico")
            texto_seguro, sensibilidade_saida = _sanitizar_texto_evidencia(chunk.get("text", ""), sensibilidade_original)
            metadata_segura = dict(metadata)
            metadata_segura["sensitivity"] = sensibilidade_saida

            evidencias.append(
                {
                    "chunk_id": item["chunk_id"],
                    "text": texto_seguro,
                    "rrf_score": round(item["rrf_score"], 6),
                    "rerank_score": item.get("rerank_score"),
                    "retrieval_sources": item["retrieval_sources"],
                    "dense_distance": item.get("dense_distance"),
                    "bm25_score": item.get("bm25_score"),
                    "source_file": metadata.get("source_file"),
                    "doc_type": metadata.get("doc_type"),
                    "sensitivity": sensibilidade_saida,
                    "base_id": metadata.get("base_id"),
                    "natureza": identificar_natureza(chunk),
                    "metadata": metadata_segura,
                }
            )

        observacao_fusao["output"] = {
            "dense_candidates": len(resultados_densos),
            "bm25_candidates": len(resultados_bm25),
            "rrf_candidates": len(ranking_rrf),
            "politica_selecao": "cobertura_definicao_normativa_v1",
            "politica_cobertura_metodos": "escopo_normativo_sem_rerank_v1",
            "cobertura_metodos_habilitada": cobertura_metodos_habilitada,
            "cobertura_metodos_aplicada": (
                ids_antes_metodos != ids_apos_metodos
            ),
            "top_ids_antes_metodos": ids_antes_metodos,
            "top_ids_apos_metodos": ids_apos_metodos,
            "cobertura_definicao_aplicada": (
                ids_antes_cobertura != ids_apos_cobertura
            ),
            "top_ids_antes_cobertura": ids_antes_cobertura,
            "top_ids_apos_cobertura": ids_apos_cobertura,
            "politica_cobertura_campos": "campos_ata_escopo_v1",
            "cobertura_campos_aplicada": (
                ids_antes_campos != ids_apos_campos
            ),
            "top_ids_antes_campos": ids_antes_campos,
            "top_ids_apos_campos": ids_apos_campos,
            "rerank_enabled": rerank.RERANK_ENABLED,
            "rerank_applied": bool(resultado_rerank.get("applied", False)),
            "rerank_status": resultado_rerank.get(
                "status", "unknown"
            ),
            "rerank_details": resultado_rerank,
            "returned": len(evidencias),
        }

    resultado = {
        "query": pergunta,
        "query_id": query_id,
        "routes": rotas,
        "filters": filtros,
        "router_justification": analise.get("justification"),
        "router_fallback": analise.get("router_fallback", False),
        "is_refusal": False,
        "refusal_reason": None,
        "evidences": evidencias,
        "retrieval_summary": {
            "dense_candidates": len(resultados_densos),
            "bm25_candidates": len(resultados_bm25),
            "rrf_candidates": len(ranking_rrf),
            "returned": len(evidencias),
        },
        "stage": "fusao_rrf",
        "latencia_ms": round((time.perf_counter() - inicio) * 1000, 2),
    }

    return _validar_com_retrieval_result(resultado)

if __name__ == "__main__":
    consulta = input("Digite uma pergunta: ")
    resultado = recuperar_evidencias(pergunta=consulta, top_k=5)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
