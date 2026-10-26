# Validação do fallback de rerank — 13/10/2026

## Correção realizada

- Removida a inversão simulada dos candidatos e as pontuações fictícias.
- Preservada a ordem e a lista completa de candidatos do RRF no fallback.
- Mantida a seleção final pelo recuperador, respeitando top_k e as rotas.
- Removida a alteração global de TOP_K na integração.
- Registrados rerank_applied=false e o motivo do fallback.
- Mantida a etapa fusao_rrf quando nenhum rerank real foi aplicado.

## Validação

- 38 testes específicos aprovados, incluindo o fluxo offline do recuperador.
- 368 testes aprovados na suíte com exclusão de testes/teste_integracao.py.
- git diff --check sem erros.
- Testes verificam a preservação de candidatos de outra rota que aparecem
  depois dos primeiros 20 resultados.
- Artefatos utilizados nos testes de compatibilidade: pacote revisado
  corpus_v3_revisado_2026-10-13, disponível no Drive.
- Nenhuma chamada aos modelos foi realizada nesta validação.

## Limitações e próximas etapas

O rerank real ainda não está implementado nesta correção. Ativar a
configuração mantém o fallback e registra esse estado explicitamente.

A implementação do serviço exige confirmação do endpoint e do contrato
de requisição e resposta. A comparação de relevância com rerank real
permanece pendente.

Os testes offline não comprovam a qualidade das respostas das personas
com os modelos reais. Essa avaliação permanece pendente.
