# Revisão de Metadados e Recorte Indexado (Corpus v3)
**Responsável:** Eridalgo Ramos da Silva
**Data:** 13 de Outubro de 2026

## 1. Auditoria de Metadados e Campos Ausentes
Durante o processamento do corpus v3 (geração do `chunks_teste.json`), foi realizada uma auditoria de integridade para validar a presença de campos obrigatórios e a correta atribuição de metadados de classificação e sensibilidade.

**Relatório de Inconsistências (Base Estruturada PNCP):**
* `sem_id_pncp`: 0 registros afetados.
* `sem_valor`: 0 registros afetados.
* `sem_ano_compra`: 0 registros afetados.
* `sem_data_publicacao`: 0 registros afetados.
A base encontra-se 100% íntegra quanto aos identificadores e datas obrigatórias.

**Distribuição por Natureza Documental:**
* **Estruturada:** 1.358 chunks
* **Agregada:** 519 chunks
* **Normativa:** 217 chunks
* **Conversacional:** 31 chunks

**Distribuição por Sensibilidade:**
* **Público:** 2.094 chunks (estruturada, normativa e agregada).
* **Restrito:** 31 chunks (exclusivamente natureza conversacional/atas, exigindo sanitização na recuperação).

## 2. Recorte Efetivamente Indexado vs. Arquivos Completos
O índice vetorial FAISS e o índice léxico BM25 da versão v3 foram construídos utilizando um **recorte de 2.125 chunks**, que difere do tamanho total dos arquivos originais utilizados nos cálculos gerais do projeto.

**Diferenciação do Recorte Agregado:**
* O arquivo original de Plano de Contratações Anual (`pca_2026_estado_rj.csv`) contém milhares de registros (aprox. 36.994 linhas). No entanto, por restrições experimentais e de otimização de cache, **apenas os primeiros 500 registros** foram ingeridos e indexados.
* O arquivo `itens_pe_038_26_2026.csv`, que engloba os itens do pregão de referência, foi **100% indexado (19 chunks)**, garantindo a correspondência técnica avaliada nos testes M01.

Este recorte garante um ambiente controlado para a validação das rotas do Adaptive RAG, mantendo a reprodutibilidade dos índices sem onerar a memória do ambiente de execução.
