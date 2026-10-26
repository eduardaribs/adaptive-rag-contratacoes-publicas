# Responsabilidades e alinhamento da equipe

**Grupo:** 1
**Projeto:** RAG para consultas sobre contratações públicas do Rio de Janeiro
**Atualização:** 05/10/2026

## Objetivo deste documento

Explicar a responsabilidade de cada integrante e como as entregas se conectam.
Na apresentação, todos devem compreender o projeto completo, além de sua
própria atividade.

Os estados abaixo refletem as entregas e validações relatadas até esta data.
Cada responsável deve conferir e atualizar sua seção quando houver avanços.

## Visão geral do projeto

O sistema recebe uma pergunta, identifica quais dados e estratégias devem ser
utilizados e apresenta um resultado sustentado pelas fontes disponíveis.

Há dois caminhos principais:

- Consulta estruturada ao JSON para contagens e listagens sobre o conjunto
  completo de registros disponíveis.
- Recuperação híbrida com Dense, BM25 e fusão RRF para perguntas abertas e
  consultas documentais.

A interface apresenta os resultados e permite registrar feedback.
Testes e logs ajudam a conferir o funcionamento e rastrear as consultas.

A consulta estruturada está implementada nos módulos, mas sua integração
com a interface ainda está pendente nesta atualização.

## Responsabilidades individuais

### Eduarda — integração, interface e coordenação

**Responsabilidade**

Integrar as entregas, apresentar os resultados ao usuário pela interface,
coordenar as validações e organizar o trabalho da equipe.

**O que recebe**

- Dados e critérios de avaliação organizados por Janice.
- Artefatos e metadados preparados pela ingestão e indexação.
- Resultados do roteador e executor desenvolvidos por Luiz.
- Evidências dos testes e logs acompanhados por Felipe.
- Resultados da reprodução do ambiente realizada por Calvin.

**O que entrega**

Interface para consulta e feedback, integração dos módulos, demonstração
do fluxo e registro do estado geral do projeto.

**Situação atual**

A interface e o feedback persistido foram testados anteriormente.
Eduarda apoiou a implementação e a validação das consultas estruturadas.
A conexão do novo executor com a interface permanece pendente.

**Na apresentação**

Explicar o problema atendido, a experiência do usuário, o fluxo geral e
como as entregas dos colegas chegam à interface.

### Janice — corpus, personas e avaliação

**Responsabilidade**

Organizar as fontes, identificar as versões do corpus, definir perguntas
compatíveis com as personas e avaliar a qualidade dos resultados.

**O que recebe**

Necessidades dos usuários, limitações do pipeline e resultados das consultas
executadas pela equipe.

**O que entrega**

Corpus identificado, perguntas de avaliação, critérios esperados e relatórios
com resultados e limitações.

**Situação atual**

Foram disponibilizados os casos P01–P09 e M01 e relatórios sobre o corpus v3.
A indexação experimental relatada cobre 140 registros, não todo o corpus.
O critério de serviços de tecnologia ainda precisa ser alinhado e validado.

**Na apresentação**

Explicar a origem dos dados, as quatro naturezas, a diferença entre versões
do corpus e como as personas orientam as respostas esperadas.

### Eridalgo — ingestão, metadados e rerank

**Responsabilidade**

Preparar os registros e chunks para consulta, preencher os metadados e
desenvolver a etapa de rerank.

**O que recebe**

Arquivos e organização do corpus, requisitos de filtros e necessidades
das consultas definidas pela equipe.

**O que entrega**

Chunks, base estruturada normalizada, metadados e módulo de rerank.
Os índices precisam ser compatíveis com os chunks utilizados.

**Situação atual**

A ingestão gera a base estruturada normalizada e preserva valores estimados
e homologados, distinguindo zero de ausência.
Foi identificado uso da data de atualização como data de publicação em
parte dos registros; a correção definitiva da ingestão está pendente.
O rerank permanece simulado e desativado por padrão.

**Na apresentação**

Explicar como os arquivos viram registros e chunks, quais metadados
permitem filtrar e quais limitações permanecem na preparação dos dados
e no rerank.

### Luiz — roteamento e execução da consulta

**Responsabilidade**

Interpretar a pergunta e identificar base, estratégia, operação, filtros
e campos de saída, executando a consulta adequada.

**O que recebe**

Registros normalizados e metadados da ingestão, índices da recuperação
e perguntas das personas.

**O que entrega**

Contagens calculadas, listagens paginadas, referências às fontes e
resultados da recuperação híbrida.

**Situação atual**

Foram implementados planejamento, consulta estruturada, seleção de campos,
paginação e reutilização da análise do roteador.
Contagem e listagem consultam toda a base fornecida e não dependem de top_k.
A recuperação híbrida foi mantida, mas a busca por vidraça ainda apresenta
problemas de relevância.
A combinação das duas estratégias em uma mesma consulta permanece pendente.

**Na apresentação**

Explicar por que contagem e listagem usam consulta ao JSON, quando a busca
híbrida é adequada e como a interpretação da pergunta controla a execução.

### Felipe — testes e observabilidade

**Responsabilidade**

Verificar o funcionamento integrado, analisar os logs e ampliar a
observabilidade da recuperação.

**O que recebe**

Versões integradas dos módulos, casos de avaliação e eventos do pipeline.

**O que entrega**

Resultados de testes, identificação de falhas e informações que permitam
acompanhar as etapas de uma consulta.

**Situação atual**

Foram relatados nove testes de integração aprovados em uma versão anterior.
As melhorias dos eventos Dense e BM25 estavam em andamento.
A etapa consulta_estruturada já possui log persistido e testes na nova
implementação; ainda é necessário validar o conjunto após a integração.

**Na apresentação**

Explicar o que os testes comprovam, como run_id e query_id relacionam
eventos e como localizar a etapa responsável por uma falha.

### Calvin — reprodução e documentação

**Responsabilidade**

Executar o projeto em ambiente limpo, seguindo o guia, e corrigir instruções,
dependências ou exemplos de configuração necessários.

**O que recebe**

Repositório, requirements.txt, .env.example, guia e acesso compartilhado
ao corpus e aos artefatos.

**O que entrega**

Guia atualizado e registro da execução com comandos, resultados,
dificuldades e etapas não concluídas.

**Situação atual**

O acompanhamento registra análise das etapas de preparação e restauração.
Calvin informou execução de testes, mas a reprodução completa ainda não
foi comprovada com resultados detalhados.
Foi preparado um roteiro para execução no VS Code.

**Na apresentação**

Explicar como outra pessoa inicia o projeto, quais artefatos externos são
necessários e quais instruções foram efetivamente testadas.

## Referências de validação

Os resultados abaixo pertencem ao recorte v2 utilizado nas consultas.
Não representam validação completa do corpus v3.

| Verificação | Resultado observado |
|---|---:|
| Arquivos de origem do recorte v2 | 8 |
| Chunks e IDs do recorte v2 | 2.125 |
| Registros estruturados | 1.358 |
| Registros com ano da compra 2026 | 1.234 |
| Município Rio de Janeiro e ano da compra 2026 | 665 |
| Ano 2026 e valor estimado acima de R$ 500 mil | 560 |
| RJ, modalidade 6 e publicação original em março de 2026 | 1.358 |
| Suíte offline após as alterações | 185 testes aprovados |

A suíte de 185 testes excluiu testes/teste_integracao.py.
Os resultados anteriores de integração devem ser associados à versão
em que foram executados.

O critério textual inicial de tecnologia encontrou 48 correspondências.
Esse número não é uma classificação validada de serviços de tecnologia.

O corpus v3 relatado por Janice contém 38.619 chunks.
A experiência com 140 embeddings é parcial e não representa sua indexação completa.

## Roteiro da apresentação

Cada integrante deve explicar:

1. Sua responsabilidade e a finalidade da etapa.
2. O que recebe dos colegas.
3. O que entrega para as etapas seguintes.
4. Um resultado ou teste que sustenta sua explicação.
5. O que está pronto, parcial ou pendente.

Ordem sugerida: Eduarda, Janice, Eridalgo, Luiz, Felipe e Calvin.
Eduarda abre com a visão geral e encerra com as pendências e próximos passos.

## Conhecimentos compartilhados

Todos devem conseguir explicar:

- Diferença entre arquivo, registro e chunk.
- Diferença entre o recorte v2 utilizado e o corpus v3 ampliado.
- Quando utilizar consulta estruturada ou recuperação híbrida.
- Por que top_k não deve limitar uma contagem.
- Diferença entre ano da compra, publicação e atualização.
- Como conferir fonte e evidência de uma resposta.
- Como rastrear uma consulta com query_id e run_id.
- O que os testes executados comprovam e o que não foi validado.
- Quais funcionalidades ainda são simuladas ou não estão integradas.

## Pendências de integração e qualidade

- Conectar o executor estruturado à interface.
- Validar o critério de serviços de tecnologia.
- Melhorar a relevância da recuperação para perguntas abertas.
- Corrigir a data de publicação na ingestão.
- Revisar o fallback do rerank e sua interação com a seleção multirrota.
- Validar consultas que precisem combinar estratégias.
- Executar os testes de integração na versão final.
- Concluir a reprodução do projeto e atualizar o guia existente.
