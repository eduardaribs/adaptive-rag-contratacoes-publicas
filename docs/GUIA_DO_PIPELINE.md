# Guia do Pipeline

Este documento apresenta o funcionamento geral do sistema para facilitar o desenvolvimento, os testes e a integração dos módulos.

---

## 1. Objetivo do sistema

O projeto implementa um sistema de **Adaptive RAG** para responder perguntas sobre contratações públicas do Estado do Rio de Janeiro.

O sistema identifica qual tipo de evidência é necessário e escolhe uma ou mais bases antes de executar a recuperação:

- **Normativa:** leis, decretos e editais;
- **Estruturada:** contratos e contratações;
- **Conversacional:** atas e comunicações;
- **Agregada:** indicadores, totais e valores agrupados.

---

## 2. Fluxo geral

```text
Pergunta do usuário
        |
        v
router.py
        |
        v
retrieve.py
        |
        v
generate.py
        |
        v
schema.py
        |
        v
Interface
```

O `obs.py` acompanha as etapas e registra os eventos em logs estruturados.

---

## 3. Responsabilidade de cada módulo

| Módulo | Entrada | Saída | Responsável |
|---|---|---|---|
| `fetch_corpus.py` | Manifesto do corpus | Corpus coletado e versionado | Janice |
| `ingest.py` | Documentos coletados | Chunks com metadados | Eridalgo |
| `index.py` | Chunks | Índices FAISS e BM25 | Eridalgo |
| `router.py` | Pergunta do usuário | Rotas, filtros e decisão de recusa | Luiz Carlos |
| `retrieve.py` | Pergunta, rotas e filtros | Evidências recuperadas | Luiz Carlos |
| `schema.py` | Dados compartilhados | Objetos validados | Felipe e Calvin |
| `generate.py` | Pergunta e evidências | Resposta fundamentada ou recusa | Felipe e Calvin |
| `obs.py` | Eventos dos módulos | Logs estruturados em JSONL | Maria Eduarda |
| `app/` | Pergunta do usuário | Resposta e evidências na interface | Maria Eduarda |

Todos devem compreender o objetivo geral do sistema, mas cada responsável deverá aprofundar a implementação e os testes de seu módulo.

---

## 4. Preparação do corpus

### 4.1 Coleta — `fetch_corpus.py`

O módulo coleta e versiona os documentos descritos no `corpus_manifest.yaml`.

**Entrada:**

- manifesto do corpus.

**Saída:**

- arquivos em `data/raw/vN/`;
- inventário da versão;
- registro de falhas;
- comparação entre versões.

### 4.2 Ingestão — `ingest.py`

O módulo lê os documentos coletados, extrai o conteúdo e gera os chunks.

Todo chunk deve possuir:

- `source_file`;
- `doc_type`;
- `chunk_id`;
- `sensitivity`;
- `base_id`.

### 4.3 Indexação — `index.py`

O módulo recebe os chunks e gera:

- embeddings;
- índice vetorial FAISS;
- índice lexical BM25;
- lista de identificadores;
- cache e arquivos persistidos.

---

## 5. Processamento de uma pergunta

### 5.1 Roteamento — `router.py`

O roteador recebe a pergunta e determina:

- quais bases devem ser consultadas;
- quais filtros foram encontrados;
- se são necessárias múltiplas bases;
- se a solicitação deve ser recusada.

Exemplo de entrada:

```python
pergunta = "Quantos contratos foram assinados por modalidade em 2025?"
```

Saída simplificada esperada:

```python
{
    "routes": ["agregada", "estruturada"],
    "filters": {"ano": 2025},
    "is_refusal": False,
    "refusal_reason": None
}
```

Exemplo de recusa:

```python
pergunta = "Esse contrato foi uma fraude?"
```

Saída simplificada esperada:

```python
{
    "routes": [],
    "filters": {},
    "is_refusal": True,
    "refusal_reason": "O sistema não pode emitir julgamento sobre fraude."
}
```

### 5.2 Recuperação — `retrieve.py`

O módulo utiliza a pergunta, as rotas e os filtros para recuperar os chunks mais relevantes.

A recuperação combina:

- busca densa com embeddings e FAISS;
- busca lexical com BM25;
- filtros por metadados;
- fusão dos rankings com RRF.

Entrada conceitual:

```python
{
    "question": "Quais contratações de tecnologia foram encontradas?",
    "routes": ["estruturada"],
    "filters": {},
    "top_k": 5
}
```

Saída simplificada:

```python
{
    "evidences": [
        {
            "chunk_id": "contrato_001",
            "text": "Contratação de serviços de tecnologia...",
            "metadata": {
                "base_id": "contratos_estruturado",
                "doc_type": "contrato",
                "ano": 2025
            },
            "score": 0.032
        }
    ]
}
```

O `retrieve.py` não produz a resposta final. Ele retorna evidências para o módulo de geração.

### 5.3 Geração e guardrails — `generate.py`

O módulo deverá:

- produzir resposta baseada nas evidências;
- informar as fontes utilizadas;
- evitar afirmações sem evidências;
- mascarar dados pessoais;
- recusar solicitações proibidas;
- informar quando não houver evidências suficientes.

Entrada conceitual:

```python
{
    "question": "Quais contratações de tecnologia foram encontradas?",
    "routes": ["estruturada"],
    "evidences": [
        {
            "chunk_id": "contrato_001",
            "text": "Contratação de serviços de tecnologia...",
            "metadata": {
                "base_id": "contratos_estruturado"
            }
        }
    ]
}
```

Saída esperada:

```python
{
    "answer": "Foram encontradas contratações relacionadas a serviços de tecnologia.",
    "sources_used": ["contrato_001"],
    "is_refusal": False,
    "refusal_reason": None
}
```

Saída em caso de recusa:

```python
{
    "answer": "Não posso emitir uma acusação de fraude.",
    "sources_used": [],
    "is_refusal": True,
    "refusal_reason": "A pergunta solicita julgamento sobre possível fraude."
}
```

Regra obrigatória:

```text
Se is_refusal for True, sources_used deve ser uma lista vazia.
```

### 5.4 Schemas — `schema.py`

O módulo define e valida os formatos dos objetos compartilhados pelo pipeline.

Os schemas devem contemplar:

- chunks;
- evidências;
- decisão do roteador;
- resposta final;
- fontes utilizadas;
- motivo de recusa.

Exemplo conceitual:

```python
from typing import List, Optional
from pydantic import BaseModel

class RAGResponse(BaseModel):
    answer: str
    sources_used: List[str]
    is_refusal: bool
    refusal_reason: Optional[str] = None
```

### 5.5 Observabilidade — `obs.py`

O módulo registra a execução do pipeline em JSONL.

Cada execução deve registrar:

- `run_id`;
- `query_id`;
- estágio;
- status;
- latência;
- modelo;
- consumo de tokens;
- informações adicionais.

Estágios padronizados:

- `query_analysis`;
- `roteamento`;
- `retrieval_denso`;
- `retrieval_bm25`;
- `fusao_rrf`;
- `rerank`;
- `geracao`;
- `validacao`;
- `feedback`.

### 5.6 Interface — `app/`

A interface apresenta:

- resposta;
- rotas selecionadas;
- filtros;
- fontes;
- evidências;
- motivo da recusa.

Enquanto o `generate.py` não estiver pronto, a interface poderá operar provisoriamente somente com roteamento e recuperação.

---

## 6. Estratégia de testes

Os testes serão armazenados em `tests/` e executados com `pytest`.

### 6.1 Testes unitários

Verificam funções isoladas e determinísticas.

Não devem depender de:

- internet;
- endpoint do LLM;
- servidor de embeddings;
- corpus completo.

Exemplos:

- cálculo do RRF;
- normalização de filtros;
- regra de recusa;
- mascaramento de dados;
- validação de metadados.

Exemplo:

```python
def test_recusa_nao_possui_fontes():
    resposta = {
        "answer": "Não posso emitir uma acusação de fraude.",
        "sources_used": [],
        "is_refusal": True,
        "refusal_reason": "Solicitação de julgamento sobre fraude."
    }

    assert resposta["is_refusal"] is True
    assert resposta["sources_used"] == []
```

### 6.2 Testes de contrato

Verificam se as entradas e saídas respeitam os formatos definidos.

Exemplos:

- todo chunk possui os metadados obrigatórios;
- toda resposta é válida segundo `RAGResponse`;
- toda recusa possui `sources_used=[]`;
- toda evidência possui identificador, texto e metadados.

Exemplo:

```python
def test_todo_chunk_tem_metadados_obrigatorios():
    chunk = {
        "chunk_id": "contrato_001",
        "text": "Exemplo de contratação.",
        "metadata": {
            "source_file": "contrato_001.json",
            "doc_type": "contrato",
            "chunk_id": "contrato_001",
            "sensitivity": "publico",
            "base_id": "contratos_estruturado"
        }
    }

    obrigatorios = {
        "source_file",
        "doc_type",
        "chunk_id",
        "sensitivity",
        "base_id"
    }

    faltando = obrigatorios - set(chunk["metadata"])

    assert not faltando
```

### 6.3 Testes de integração

Executam o pipeline completo com três perguntas conhecidas.

Devem ser marcados com:

```python
import pytest

@pytest.mark.llm
def test_pipeline_com_pergunta_conhecida():
    pass
```

Os testes de integração serão finalizados depois que os módulos principais estiverem conectados.

Testes que dependem de rede ou LLM não devem executar por padrão.

---

## 7. Fixtures

A pasta `tests/fixtures/` deverá conter aproximadamente 20 documentos pequenos e versionados.

As fixtures permitem testar sem depender da rede ou do corpus completo.

Devem existir exemplos das quatro bases:

- normativa;
- estruturada;
- conversacional;
- agregada.

Também devem existir casos de:

- consulta comum;
- filtro por ano;
- consulta cross-source;
- dado pessoal a ser mascarado;
- pergunta de recusa;
- ausência de evidências.

---

## 8. Ordem recomendada para Felipe e Calvin

1. Compreender o objetivo geral do pipeline;
2. observar a entrada e a saída do `router.py`;
3. observar a entrada e a saída do `retrieve.py`;
4. definir os modelos em `schema.py`;
5. implementar `generate.py` e os guardrails;
6. criar fixtures pequenas;
7. criar os testes unitários;
8. criar os testes de contrato;
9. integrar geração, recuperação e interface;
10. criar três testes de integração marcados com `@pytest.mark.llm`.

Não é necessário dominar a implementação interna de FAISS, BM25 ou embeddings para começar os testes de contrato e os testes de geração.

É necessário compreender:

- o que cada módulo recebe;
- o que cada módulo devolve;
- quais regras devem ser respeitadas;
- quais casos devem gerar resposta, mascaramento ou recusa.

---

## 9. Perguntas de referência

### Consulta estruturada

```text
Quais contratações de serviços de tecnologia foram encontradas?
```

Rota esperada:

```python
["estruturada"]
```

### Consulta normativa

```text
O que a Lei nº 14.133/2021 estabelece sobre o pregão eletrônico?
```

Rota esperada:

```python
["normativa"]
```

### Consulta agregada e estruturada

```text
Quantos contratos foram assinados por modalidade em 2025?
```

Rotas esperadas:

```python
["agregada", "estruturada"]
```

### Consulta conversacional

```text
O que foi discutido nas atas sobre a compra de equipamentos?
```

Rota esperada:

```python
["conversacional"]
```

### Consulta cross-source

```text
Sou MEI, posso participar de pregão eletrônico e existe algum aberto para material de escritório?
```

Rotas esperadas:

```python
["estruturada", "normativa"]
```

### Consulta que exige recusa

```text
Esse contrato foi uma fraude?
```

Resultado esperado:

```python
{
    "routes": [],
    "is_refusal": True,
    "evidences": []
}
```

---

## 10. Comandos para os testes

Instalar dependências:

```bash
pip install -r requirements.txt
```

Executar apenas testes offline:

```bash
pytest -m "not llm" -v
```

Executar testes com LLM:

```bash
pytest -m llm -v
```

Executar todos os testes:

```bash
pytest -v
```

---

## 11. Resultado esperado

Ao final, o sistema deverá:

1. analisar a pergunta;
2. selecionar uma ou mais bases;
3. extrair filtros;
4. recuperar evidências relevantes;
5. gerar uma resposta fundamentada;
6. apresentar as fontes;
7. aplicar mascaramento ou recusa;
8. registrar as etapas em logs estruturados;
9. permitir avaliação por testes reproduzíveis.
