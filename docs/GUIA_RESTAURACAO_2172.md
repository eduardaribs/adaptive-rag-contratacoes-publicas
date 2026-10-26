# Restauração do pacote de 2.172 chunks

## Identificação

Pasta compartilhada: ENTREGA_EQUIPE_2026-10-16/pacote_v3_2172.
Confirme o acesso pelo link da equipe. O caminho no Drive montado pode variar
entre integrantes.

Código funcional avaliado: fef6d7a26ea24175af8c9e593425d2b7af980aa0.
A entrega final ainda não está congelada.

O pacote contém oito arquivos brutos e 14 arquivos de dados no manifesto.
São 2.172 chunks e IDs únicos; FAISS com 2.172 vetores de dimensão 1.024;
BM25 com 2.172 documentos.

Distribuição: 1.358 estruturados, 519 agregados, 217 normativos e
78 conversacionais. Não misturar com o pacote histórico de 2.125 chunks.

## Procedimento

Obtenha um clone em commit identificado, instale as dependências em ambiente
isolado e obtenha o pacote completo. Execute da raiz do clone, ajustando PACOTE.
O procedimento verifica hashes antes de carregar índices ou pickle e não
sobrescreve arquivos diferentes.

```python
from pathlib import Path
import hashlib
import json
import shutil

PACOTE = Path("/caminho/para/pacote_v3_2172").resolve()
REPO = Path.cwd().resolve()
manifesto = json.loads(
    (PACOTE / "MANIFESTO_SHA256.json").read_text(encoding="utf-8")
)
assert manifesto["chunks"] == 2172
assert len(manifesto["arquivos"]) == 14

def sha256(arquivo):
    calculo = hashlib.sha256()
    with arquivo.open("rb") as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
            calculo.update(bloco)
    return calculo.hexdigest()

pares = []
for nome, esperado in manifesto["arquivos"].items():
    relativo = Path(nome)
    assert not relativo.is_absolute() and ".." not in relativo.parts
    assert relativo.parts[0] == "data"
    origem = (PACOTE / relativo).resolve()
    destino = (REPO / relativo).resolve()
    assert origem.is_relative_to(PACOTE)
    assert destino.is_relative_to(REPO)
    assert origem.is_file()
    assert sha256(origem) == esperado["sha256"], nome
    if destino.exists():
        assert destino.is_file()
        assert sha256(destino) == esperado["sha256"], (
            f"Preserve o arquivo diferente antes de restaurar: {nome}"
        )
    pares.append((origem, destino, esperado["sha256"]))

for origem, destino, esperado in pares:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        shutil.copy2(origem, destino)
    assert sha256(destino) == esperado

from src.retrieve import carregar_artefatos

chunks, por_id, ids, faiss, bm25 = carregar_artefatos()
assert len(chunks) == len(por_id) == len(ids) == len(set(ids)) == 2172
assert faiss.ntotal == 2172 and faiss.d == 1024
assert bm25.corpus_size == 2172
print("Pacote restaurado e carregado sem reindexação.")
```

## Configuração

Configure o serviço conforme .env.example, sem versionar credenciais.
Defina antes de importar a aplicação:

- RAG_DEMO_OFFLINE=false
- LLM_REASONING_EFFORT=none
- ROUTER_MAX_TOKENS=512
- RERANK_ENABLED=false
- PIPELINE_LOG_DIR: pasta persistente de logs
- HISTORY_PATH: banco SQLite persistente
- FEEDBACK_PATH: arquivo JSONL persistente

Atribua também src.obs.PASTA_LOGS à pasta de logs na inicialização.
O histórico é compartilhado por quem acessa a mesma instância.

## Limites e estado da reprodução

- Os cálculos usam os CSV completos; top_k limita evidências documentais.
- Os 519 chunks agregados não representam todas as 36.994 linhas do PCA.
- O recorte do PCA depende da exportação disponibilizada pela equipe.
- UF identifica a unidade administrativa, não necessariamente a execução.
- Ano da compra, publicação e vigência são informações distintas.
- Campos de vigência previstos no manifesto podem estar vazios nos chunks.
- A redação normativa é um snapshot, sem garantia de vigência atual.
- A busca de vínculos por identificadores não prova inexistência de relações.
- Foi observado timeout de roteamento seguido de cálculo correto por fallback.
- O prefixo de lista '1. ' levou a esclarecimento em uma pergunta agregada.
- Houve timeout no JavaScript externo da Gradio 6.29.0. Um contorno de
  template foi testado somente no processo; sua inicialização deve ser
  documentada para a reprodução.
- Rerank comparado em seis rankings salvos; respostas com rerank ainda
  não tiveram sua qualidade comparada.
- Reprodução final por outro integrante e congelamento permanecem pendentes.

O ambiente observado usa Python 3.13.16 e Gradio 6.29.0.
requirements.txt define mínimos, não um lockfile.
Não executar ingestão ou indexação para restaurar este pacote.


## Inicialização Colab com frontend local

O inicializador preservado em scripts/iniciar_interface_colab.py usa
os arquivos locais do frontend da Gradio, com ajuste restrito ao processo.
Foi utilizado para contornar o timeout de gradio.js externo na Gradio 6.29.0.

Antes de executá-lo, configure PIPELINE_LOG_DIR, HISTORY_PATH,
FEEDBACK_PATH e GRADIO_SERVER_PORT no ambiente do processo.

Execute da raiz do repositório:
python scripts/iniciar_interface_colab.py

Esse script inicia a aplicação e publica um link temporário. Use pastas
persistentes apropriadas e considere que o histórico é compartilhado
por quem acessa a instância.

As versões observadas estão em docs/ambiente_validacao_2026-10-19.
requirements-base.txt registra dependências diretas e algumas dependências
de interface. requirements-rerank.txt registra as opcionais do rerank.
Esses arquivos precisam ser exercitados na reprodução final.
