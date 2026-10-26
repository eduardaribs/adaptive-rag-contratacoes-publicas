# Instruções de Geração e Carregamento de Artefatos (v3)

## 1. Geração dos Artefatos
Para reproduzir a ingestão e indexação do zero, garantindo a integridade do cache:
1. **Ingestão:** Execute `python src/ingest.py`. O script processa os arquivos brutos v3 e gera `chunks_teste.json`.
2. **Indexação:** Execute `python src/index.py`. O sistema criará as chaves de cache (SHA-256) para cada chunk. Os embeddings só serão recalculados via API se o texto ou o modelo sofrerem alterações.
3. **Saída:** Os artefatos finais (`faiss_index.bin`, `bm25_index.pkl`, `chunk_ids.json` e `cache_embeddings.json`) são consolidados no disco.

## 2. Carregamento (Recuperação)
Durante as consultas, o módulo `src/retrieve.py` utiliza a função `carregar_artefatos()` para carregar os índices vetoriais e léxicos diretamente da memória persistente. **Nenhum índice é recriado em tempo de execução**, garantindo baixa latência e preservando os artefatos em disco.

## Correção do fluxo v3 — 13/10/2026

A ingestão processa os oito arquivos das quatro naturezas em
`data/raw/v3/`. Arquivos ausentes ou fontes sem chunks
interrompem a execução sem publicar chunks completos.

### Caminhos utilizados

- Chunks: `data/processed/chunks_teste.json`.
- Base: `data/processed/base_estruturada_normalizada.json`.
- Índices, IDs e cache: `data/indices/`.

Na raiz do repositório, execute `python src/ingest.py`
e depois `python src/index.py`.
Esses comandos escrevem nos destinos usados pela aplicação.

Para validar separadamente, utilize outro diretório de trabalho
contendo os oito arquivos em `data/raw/v3/`.
Importe o código do repositório e chame:

- `rodar_ingestao_hibrida(versao='v3', pasta_saida='data/processed')`.
- `gerar_indices(caminho_entrada='data/processed/chunks_teste.json',
  pasta_indices='data/indices')`.

Os caminhos relativos dependem do diretório atual.
Ingestão, indexação e empacotamento devem utilizar
a mesma pasta de trabalho.

### Cache e procedência

O cache utiliza chaves baseadas em ID, texto e modelo.
O cache antigo por ID não é automaticamente compatível
e pode provocar novas chamadas à API.

Na auditoria do pacote anterior, 44 vetores possuem modelo
registrado e 2.081 têm origem histórica sem modelo comprovado.
Não atribuir um modelo aos vetores de procedência desconhecida.

Registros JSON equivalentes podem ter textos serializados
diferentes. Reutilização exige conferir o texto associado ao vetor.

### Restauração e geração

Restaurar pelo Drive carrega artefatos existentes.
Gerar novamente executa ingestão e indexação e pode
exigir chamadas ao endpoint de embeddings.

Restaurar chunks, base, IDs e índices do mesmo pacote.
Não misturar chunks de uma execução com índices de outra.

### Testes com artefatos em outra pasta

Os testes de compatibilidade aceitam as variáveis `RAG_TEST_PASTA_INDICES` e `RAG_TEST_CAMINHO_CHUNKS`.
Informe os índices e os chunks do mesmo pacote validado. Sem essas variáveis, os testes usam os caminhos padrão do repositório.
