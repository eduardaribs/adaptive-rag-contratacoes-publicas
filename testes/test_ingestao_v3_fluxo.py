
import json
from pathlib import Path

import faiss
import numpy as np
import pytest

from src import ingest
from src import index as indexador


CAMINHOS = (
    "estruturada/pncp/rj/pregao_eletronico/2026-03/contratacoes_publicacao.json",
    "normativa/federal/lei_14133_2021/lei_14133_2021.html",
    "agregada/pca_2026_estado_rj.csv",
    "agregada/itens_pe_038_26_2026.csv",
    "conversacional/atas/ebserh/2026/ata_00191.pdf",
    "conversacional/atas/fiocruz/2026/ata_00001.pdf",
    "conversacional/atas/ministerio_saude/2026/ata_00137.pdf",
    "conversacional/comunicacoes_sinteticas/troca_mensagens_material_escritorio_001.txt",
)


def criar_corpus(tmp_path):
    for relativo in CAMINHOS:
        arquivo = tmp_path / "data/raw/v3" / relativo
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text("conteudo de teste", encoding="utf-8")

    registro = {
        "numeroControlePNCP": "123-1-1/2026",
        "anoCompra": 2026,
        "objetoCompra": "Computador.",
        "dataPublicacaoPncp": "2026-03-01T10:00:00",
        "valorTotalEstimado": 100,
    }
    arquivo = tmp_path / "data/raw/v3" / CAMINHOS[0]
    arquivo.write_text(json.dumps([registro]), encoding="utf-8")
    return registro


def simular_fontes_textuais(monkeypatch, chamadas, vazio=False):
    def processar(natureza):
        def executar(caminho, **kwargs):
            chamadas.append((natureza, caminho))
            if vazio:
                return []
            return [{
                "text": "Texto de teste.",
                "metadata": {
                    "chunk_id": Path(caminho).name + "_chunk_1",
                    "natureza": natureza,
                },
            }]
        return executar

    monkeypatch.setattr(
        ingest, "processar_normativa", processar("normativa")
    )
    monkeypatch.setattr(
        ingest, "processar_agregada", processar("agregada")
    )
    monkeypatch.setattr(
        ingest, "processar_conversacional", processar("conversacional")
    )


def test_ingestao_conecta_quatro_naturezas_e_saida_isolada(
    tmp_path, monkeypatch
):
    registro = criar_corpus(tmp_path)
    monkeypatch.chdir(tmp_path)
    chamadas = []
    simular_fontes_textuais(monkeypatch, chamadas)

    chunks = ingest.rodar_ingestao_hibrida(
        versao="v3", pasta_saida="saida/processed"
    )

    assert len(chunks) == 8
    assert {c["metadata"]["natureza"] for c in chunks} == {
        "estruturada", "normativa", "agregada", "conversacional"
    }
    assert len(chamadas) == 7
    assert all(c.startswith("data/raw/v3/") for _, c in chamadas)

    base = json.loads(
        Path("saida/processed/base_estruturada_normalizada.json")
        .read_text(encoding="utf-8")
    )
    assert json.loads(base[0]["texto_integral"]) == registro
    assert base[0]["fonte_original"].startswith("data/raw/v3/")
    assert Path("saida/processed/chunks_teste.json").is_file()
    assert not Path("data/processed").exists()


def test_corpus_incompleto_interrompe_antes_de_gravar(
    tmp_path, monkeypatch
):
    criar_corpus(tmp_path)
    (tmp_path / "data/raw/v3" / CAMINHOS[-1]).unlink()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="Corpus incompleto"):
        ingest.rodar_ingestao_hibrida(pasta_saida="saida/processed")

    assert not Path("saida/processed").exists()


def test_fonte_sem_chunks_nao_publica_resultado_completo(
    tmp_path, monkeypatch
):
    criar_corpus(tmp_path)
    monkeypatch.chdir(tmp_path)
    simular_fontes_textuais(monkeypatch, [], vazio=True)

    with pytest.raises(RuntimeError, match="Nenhum chunk"):
        ingest.rodar_ingestao_hibrida(pasta_saida="saida/processed")

    assert not Path("saida/processed/chunks_teste.json").exists()


def test_indexador_le_entrada_explicita_e_reutiliza_cache(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        indexador, "CACHE_FILE", str(tmp_path / "cache_original.json")
    )

    def proibir_api(*args, **kwargs):
        raise AssertionError("O cache completo deve evitar chamadas à API.")

    monkeypatch.setattr(indexador, "OpenAI", proibir_api)

    chunks = [
        {"text": "Servidor rack", "metadata": {"chunk_id": "a"}},
        {"text": "Servico digital", "metadata": {"chunk_id": "b"}},
    ]
    entrada = tmp_path / "entrada/chunks_teste.json"
    entrada.parent.mkdir()
    entrada.write_text(json.dumps(chunks), encoding="utf-8")

    saida = tmp_path / "saida/indices"
    saida.mkdir(parents=True)
    vetores = [[1.0, 0.0], [0.0, 1.0]]
    cache = {
        indexador.gerar_chave_cache(
            c["metadata"]["chunk_id"],
            c["text"],
            indexador.EMBEDDING_MODEL,
        ): vetor
        for c, vetor in zip(chunks, vetores)
    }
    (saida / "cache_embeddings.json").write_text(
        json.dumps(cache), encoding="utf-8"
    )

    indexador.gerar_indices(
        caminho_entrada=str(entrada),
        pasta_indices=str(saida),
    )

    ids = json.loads(
        (saida / "chunk_ids.json").read_text(encoding="utf-8")
    )
    assert ids == ["a", "b"]

    indice = faiss.read_index(str(saida / "faiss_index.bin"))
    assert indice.ntotal == 2
    np.testing.assert_array_equal(
        indice.reconstruct_n(0, 2),
        np.asarray(vetores, dtype=np.float32),
    )
    assert (saida / "bm25_index.pkl").is_file()
    assert not (tmp_path / "data/indices").exists()
