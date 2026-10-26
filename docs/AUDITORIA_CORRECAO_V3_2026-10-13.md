# Auditoria e correção do fluxo v3 — 13/10/2026

## Diagnóstico

O ZIP recebido de Eridalgo possui SHA-256:
`5acfb7e0a6bca0965dd3caa12f6758e31d21ed91d4f5b7ba80ae6ec1e76f47c0`.

O ZIP está íntegro, mas a base normalizada e os chunks
estruturados correspondem integralmente à coleta v2.
Os 44 registros alterados na v3 permanecem iguais à v2.

Após o merge 258a0ad, a ingestão gravava em
`data/processed/v3/`, enquanto o indexador lia
`data/processed/`. Faltavam as outras três naturezas.

## Correção e validação

- Restauradas as funções e chamadas das quatro naturezas.
- Unificados os destinos padrão e parametrizadas as saídas.
- Interrupção para corpus incompleto ou fonte sem chunks.
- Oito arquivos v3 conferidos pelos hashes do inventário.
- Ingestão isolada: 1.358 registros e 2.125 chunks.
- Estruturada: 1.358; normativa: 217;
  agregada: 519; conversacional: 31.
- Base e chunks estruturados correspondem à coleta v3.
- Origens apontam para v3; IDs únicos; 19 itens do PE.
- Sete testes específicos aprovados sem chamadas à API.

## Comparação com o pacote v3 anterior

Nenhum conteúdo divergente: 1.314 registros com
serialização diferente e 811 textos idênticos.

Na pasta de validação, as serializações equivalentes foram
alinhadas aos textos anteriores e conferidas pelo rastreio.
Isso foi uma operação de auditoria, não uma regra
automática incorporada à ingestão.

FAISS anterior: 2.125 vetores, dimensão 1.024, finitos,
não zerados e iguais ao cache na ordem dos IDs.
BM25 anterior: frequências e tamanhos correspondem
aos 2.125 textos tokenizados.

## Limitações e próximas etapas

- Modelo registrado para 44 vetores.
- Modelo não comprovado para 2.081 vetores históricos.
- Nenhum embedding novo gerado nesta correção.
- Índices ainda não reconstruídos para os IDs da nova ingestão.
- Índices anteriores conferidos com seus próprios chunks e IDs.
- Artefatos ativos da interface preservados.
- Pendente: procedência/migração do cache, empacotamento
  final e validação integrada do RAG.

## Validação da suíte

- 354 testes aprovados em 11,55 segundos.
- Excluído: `testes/teste_integracao.py`.
- Testes de compatibilidade executados com chunks e índices
  do mesmo pacote v3 previamente validado no Drive.
- `git diff --check` aprovado.
- Essa execução não comprova a reconstrução dos índices
  da nova ingestão nem a avaliação completa do RAG.
