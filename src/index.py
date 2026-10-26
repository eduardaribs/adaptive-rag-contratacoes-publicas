import os
import json
import time
import hashlib
import faiss
import numpy as np
import pickle
from openai import OpenAI
from rank_bm25 import BM25Okapi

OLLAMA_URL = "http://ecoa-llm.duckdns.org:11434/v1"
EMBEDDING_MODEL = "xagi/qwen3-embedding:0.6b-q4_k_m"
CACHE_FILE = "data/indices/cache_embeddings.json"

def gerar_chave_cache(chunk_id, texto, modelo):
    """Gera uma chave SHA-256 única baseada no ID, conteúdo e modelo."""
    conteudo_str = f"{chunk_id}|{texto}|{modelo}"
    return hashlib.sha256(conteudo_str.encode('utf-8')).hexdigest()

def carregar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)

def gerar_indices(
    caminho_entrada="data/processed/chunks_teste.json",
    pasta_indices="data/indices",
    caminho_cache=None,
):
    print("Iniciando a indexação com CACHE DE EMBEDDINGS (FAISS + BM25)...")

    global CACHE_FILE
    CACHE_FILE = caminho_cache or os.path.join(
        pasta_indices, "cache_embeddings.json"
    )
    if not os.path.exists(caminho_entrada):
        print(f"❌ Erro: Arquivo {caminho_entrada} não encontrado.")
        return

    with open(caminho_entrada, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Total de chunks para processar: {len(chunks)}")

    cache_embeddings = carregar_cache()

    textos = []
    ids_lista = []
    chunks_para_api = []
    chaves_atuais_necessarias = []

    for c in chunks:
        chunk_id = c["metadata"]["chunk_id"]
        texto = c["text"]
        textos.append(texto)
        ids_lista.append(chunk_id)

        # Gera a chave forte baseada no texto e modelo atual
        chave_forte = gerar_chave_cache(chunk_id, texto, EMBEDDING_MODEL)
        chaves_atuais_necessarias.append(chave_forte)

        # Se a chave exata não existir no cache, manda para a API gerar de novo
        if chave_forte not in cache_embeddings:
            chunks_para_api.append({"chave": chave_forte, "text": texto, "id": chunk_id})

    print(f"Chunks validados e puxados do cache local: {len(chunks) - len(chunks_para_api)}")
    print(f"Chunks que precisam ser (re)gerados na API: {len(chunks_para_api)}")

    if chunks_para_api:
        client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")
        tamanho_lote = 50

        for i in range(0, len(chunks_para_api), tamanho_lote):
            lote = chunks_para_api[i:i + tamanho_lote]
            lote_textos = [item["text"] for item in lote]

            print(f"⏳ Processando lote novo na API ({len(lote)} embeddings)...")
            try:
                response = client.embeddings.create(
                    input=lote_textos,
                    model=EMBEDDING_MODEL
                )
                for j, data in enumerate(response.data):
                    # Agora salva no dicionário usando a chave forte
                    cache_embeddings[lote[j]["chave"]] = data.embedding
            except Exception as e:
                print(f"❌ Erro ao consultar a API: {e}")

            if i + tamanho_lote < len(chunks_para_api):
                print("🛑 Aguardando 10 segundos (Rate Limiting)...")
                time.sleep(10)

        salvar_cache(cache_embeddings)
        print("💾 Arquivo de cache em disco atualizado com sucesso!")

    embeddings_finais = []
    for chave in chaves_atuais_necessarias:
        if chave in cache_embeddings:
            embeddings_finais.append(cache_embeddings[chave])
        else:
            print(f"⚠️ Erro fatal: Falha ao recuperar embedding do cache!")
            return

    print("\nConstruindo os índices finais...")
    dimensao = len(embeddings_finais[0])
    matriz_vetores = np.array(embeddings_finais).astype('float32')

    indice_faiss = faiss.IndexFlatL2(dimensao)
    indice_faiss.add(matriz_vetores)

    corpus_tokenizado = [texto.lower().split(" ") for texto in textos]
    indice_bm25 = BM25Okapi(corpus_tokenizado)

    os.makedirs(pasta_indices, exist_ok=True)
    faiss.write_index(indice_faiss, os.path.join(pasta_indices, "faiss_index.bin"))
    with open(os.path.join(pasta_indices, "bm25_index.pkl"), "wb") as f: pickle.dump(indice_bm25, f)
    with open(os.path.join(pasta_indices, "chunk_ids.json"), "w", encoding="utf-8") as f: json.dump(ids_lista, f, indent=4)

    print(f"✅ Pipeline otimizado finalizado com sucesso! (Tarefa 4 Concluída)")

if __name__ == "__main__":
    gerar_indices()
