import json
import os
from pathlib import Path

import faiss
import numpy as np


RAIZ = Path(__file__).resolve().parents[1]
PASTA_INDICES = Path(os.environ.get(
    "RAG_TEST_PASTA_INDICES", str(RAIZ / "data/indices")
))
CAMINHO_CHUNKS = Path(os.environ.get(
    "RAG_TEST_CAMINHO_CHUNKS",
    str(RAIZ / "data/processed/chunks_teste.json"),
))


def test_alinhamento_e_unicidade():
    with (PASTA_INDICES / "chunk_ids.json").open(
        encoding="utf-8"
    ) as arquivo:
        chunk_ids = json.load(arquivo)

    with CAMINHO_CHUNKS.open(encoding="utf-8") as arquivo:
        chunks = json.load(arquivo)

    indice = faiss.read_index(
        str(PASTA_INDICES / "faiss_index.bin")
    )

    assert chunk_ids, "O conjunto de IDs está vazio."
    assert len(chunk_ids) == len(chunks) == indice.ntotal, (
        "Quantidades de IDs, chunks e vetores não correspondem."
    )
    assert len(set(chunk_ids)) == len(chunk_ids), (
        "IDs duplicados encontrados."
    )
    assert [
        chunk["metadata"]["chunk_id"] for chunk in chunks
    ] == chunk_ids, "A ordem dos IDs não corresponde aos chunks."


def test_vetores_dimensao_e_valores_finitos():
    indice = faiss.read_index(
        str(PASTA_INDICES / "faiss_index.bin")
    )

    assert indice.ntotal > 0, "O índice está vazio."
    assert indice.d == 1024, (
        f"Dimensão diferente da esperada: {indice.d}"
    )

    vetores = indice.reconstruct_n(0, indice.ntotal)

    assert vetores.shape == (indice.ntotal, indice.d)
    assert np.isfinite(vetores).all(), (
        "Vetores contêm NaN ou infinito."
    )
    assert (np.linalg.norm(vetores, axis=1) > 0).all(), (
        "Há vetores zerados."
    )
