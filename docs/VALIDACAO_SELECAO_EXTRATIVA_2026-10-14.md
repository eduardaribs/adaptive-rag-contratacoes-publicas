# Validação da seleção extrativa — 14/10/2026

## Problema e correção
P04 recuperava evidências pertinentes, mas o modelo devolvia JSON
por incisos, incompatível com o contrato `chunk_ids`.

A chamada extrativa passou a solicitar saída estruturada por JSON Schema,
com IDs permitidos extraídos do contexto. A validação de IDs e citações
foi preservada.

Para perguntas normativas gerais reconhecidas, uma regra local preserva
a definição já recuperada na seleção final. A seleção do modelo é validada
antes da regra. Nenhum ID de artigo é fixado no código.

## Execução real pela interface
- Pergunta: O que a Lei nº 14.133/2021 estabelece sobre o pregão?
- Run ID: d985acc0
- Query ID: q_bb7f63ec
- Chunks citados: artigos 28, 29 e 6.
- Trechos literais e citações validados.
- Log: cobertura_definicao_aplicada=true.
- Tempo observado: aproximadamente 26,8 segundos.
- Fonte: lei_14133_2021.html.
- Artefatos: pacote anterior corpus_v3_revisado_2026-10-13,
  com 2.125 chunks e índices correspondentes.

O modelo seleciona IDs; o sistema apresenta textos originais.
A inclusão da definição nesta execução foi feita pela regra local,
não atribuída ao modelo.

## Testes
452 testes aprovados com:
`/usr/bin/python3 -m pytest -q --ignore=testes/teste_integracao.py`

Os caminhos dos testes de compatibilidade foram configurados para
os artefatos restaurados. A execução real de P04 é evidência separada
da suíte local. git diff --check sem erros.

## Limitações
O artigo 6 é apresentado inteiro, deixando a resposta longa.
A regra não verifica completude de perguntas arbitrárias.
O corpus corrigido de 2.172 chunks ainda requer índices próprios.
A duplicação de tokens nos eventos do adaptador e gerador permanece
pendente de correção; esses eventos não devem ser somados como
se representassem chamadas independentes.

## Evidência externa
Log salvo no Drive:
demonstracao_interface_2026-10-14/reserva/P04_cobertura_d985acc0.jsonl

## Apoio de IA
IA auxiliou o diagnóstico, a implementação e os testes.
A execução real e a conferência da interface foram realizadas pela integrante.
