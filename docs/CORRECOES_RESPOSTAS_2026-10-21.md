# Correções de respostas e integração — 21/10/2026

## Identificação

- Branch: `fix/respostas-explicativas-20261021T192459760154Z`.
- Base: `746c4941171ef5b25193a259d36951bf23a8c047`.
- Publicação: [PR #52](https://github.com/rag-grande-desafio-grupo1-cenario-1/repositorio1/pull/52).
- Commit das correções: `f3e25d01a8a6fe0c5aac33a86c338346696830cb`.
- Commit de integração: `2365d6bb01e937bc02a3e55a2c034eca362a9fe6`.
- Modelo observado: `qcwind/qwen3-8b-instruct-Q4-K-M`.
- Corpus preservado: 2.172 chunks; nenhum índice regenerado.
- SHA-256 de `chunks_teste.json`:
  `dcdcc7a0f8e34da1d0824b5322b6e37306c34e2d53d107c1ca067bc2771c8404`.

Este relatório consolida saídas e conferências da sessão.
Não constitui avaliação humana independente nem nova execução
das avaliações históricas.

## Correções

- Remoção da ativação automática de extração literal para normativa e atas.
- Síntese explicativa citada como padrão; modo extrativo explícito preservado.
- Planejamento analítico validado para os CSVs autorizados do PE e PCA.
- Contagens, medidas, agrupamentos, listagens e comparações determinísticas.
- Preparação do contexto documental sem regenerar índices.
- Separação dos pedidos numéricos e documentais reconhecidos.
- Impedimento de usar cálculo numérico como fonte de explicação normativa.
- Correção da tabela duplicada e atualização automática da lista do histórico.

Contratos válidos e referências reconhecidas não comprovam, isoladamente,
a pertinência do plano ou o suporte semântico da resposta.

## Casos reais identificados

| Caso | Run ID | Resultado observado |
|---|---|---|
| Resposta curta | `18c2c0fc` | 8 itens homologados, em uma frase |
| Comparação | `609a24c7` | 8 homologados, 9 fracassados; diferença -1 |
| Tabela por situação | `a723d75b` | 8 homologados, 9 fracassados e 2 desertos |
| Listagem de maior valor | `85716d54` | Itens 1, 3 e 4; três exibidos de oito correspondências |
| Média do PCA | `afe39f4f` | Soma dividida por 36.994 registros com valores presentes |
| Assinatura indisponível | `fbb7a5b0` | Esclarecimento, preservando a condição solicitada |
| Explicação normativa | `bf50d199` | Regra e exceções com referência ao chunk 29 |
| Explicação da ata | `e00398b3` | Rodízios, AGIMED e distinção entre registro e prova de entrega |
| Contagem e lei | `f87d8192` | Oito itens e explicação documental separada |
| Tabela e lei | `040fab04` | Tabela 8/9/2 e explicação documental separada |
| Reformulação com “Depois explique” | `cf7920f1` | Contagem e pedido documental preservados |
| Interface e histórico | `4c11bd77` | Pergunta e resposta reapresentadas sem tabela duplicada |

A média calculada foi
`1512908.1520876871925177055738768448937665567389306`.
O resultado se restringe ao PCA fornecido, sem comprovar abrangência integral
das contratações do RJ ou execução do planejamento.

Na ata, objeto e contratada foram sustentados pelos chunks 1 e 14.
A existência do registro de preços, isoladamente, não comprova entrega.
A ausência de informação em trechos não comprova ausência no documento completo.

As respostas normativas mantiveram a remissão ao art. 6º, inciso XXI,
alínea “a”, sem detalhar esse dispositivo. Sua explicação em linguagem
mais acessível depende de evidência apropriada.

## Testes e persistência

- Última suíte local completa informada: 754 aprovados e sete `llm` desmarcados.
- Ajuste posterior do histórico: 18 testes relacionados aprovados.
- Essa rodada parcial não equivale a uma nova suíte completa.
- Persistência conferida em processos separados: resultado integral,
  pergunta, tabela, cálculo, fontes, IDs documentais e vínculo do feedback.
- Sobrescrita de consulta existente bloqueada no teste de persistência.
- Reabertura visual da consulta `4c11bd77` confirmada.
- Consulta `8474c27d` conferida no histórico após a nova execução.
- Os sete testes de integração real foram executados separadamente nesta revisão e aprovados.

## Registros no ambiente compartilhado

Pastas sob `/content/drive/MyDrive/rag_grande_desafio/`:

- `validacao_pipeline_analitico_20261021T220919186872Z`
- `retomada_media_pipeline_20261021T221612764987Z`
- `revalidacao_documental_contexto_20261021T223141846603Z`
- `validacao_ata_contexto_pdf_20261021T224042323294Z`
- `revalidacao_combinada_separacao_20261021T225640936795Z`
- `validacao_persistencia_analitica_20261021T230230991919Z`
- `correcao_tabela_duplicada_20261021T230845694033Z`
- `atualizacao_automatica_historico_20261021T232345467758Z`

São caminhos dos registros completos no Drive, não links públicos
nem arquivos automaticamente incluídos no Git.

## Limitações e fechamento

- Conferência do histórico realizada com a consulta `8474c27d`.
- Revisão dos módulos de integração, cálculos e contexto realizada.
- Verificações locais e reais concluídas nos registros identificados.
- Correções publicadas e integradas pelo PR #52; tag de 19/10 preservada.
- Preservar pendências anteriores sem evidência de conclusão.
- A interpretação de linguagem natural permanece sujeita a erros.
- A proteção de condições ausentes cobre conceitos conhecidos.
- Orçamentos de contexto podem excluir evidências necessárias.
- Não houve nova avaliação completa de todas as personas nesta revisão.
- Casos aprovados não comprovam atendimento universal.

## Consolidação da validação — 21/10/2026

Após o ajuste do indicador de conclusão das consultas combinadas, a suíte local completa teve **754 testes aprovados e sete `llm` desmarcados**. Em uma execução separada, os **sete testes de integração real foram aprovados**.

A interface respondeu à pergunta simples sobre homologações com oito itens, sem exigir instrução de tamanho da resposta. A consulta `8474c27d`, `query_id=q_10d777d6`, apareceu no histórico na conferência solicitada. A reabertura e a apresentação sem tabela duplicada já haviam sido conferidas na consulta `4c11bd77`.

A rodada parcial anterior de 18 testes foi seguida pela suíte completa de 754 testes. Os sete testes reais são uma rodada separada; não constituem avaliação universal das perguntas ou nova avaliação completa das personas.

Registros: [evidências](validacao_respostas_2026-10-21/evidencias.json). Publicação confirmada pelo [PR #52](https://github.com/rag-grande-desafio-grupo1-cenario-1/repositorio1/pull/52), integrado à `main` no commit `2365d6bb01e937bc02a3e55a2c034eca362a9fe6`. O commit das correções é `f3e25d01a8a6fe0c5aac33a86c338346696830cb`.
