# Consulta combinada e limites de chamada — 14/10/2026

## Correções
- Decomposição de uma forma explícita de pergunta combinada antes
  da recuperação documental, compartilhada com a preparação da geração.
- Pergunta original preservada no resultado; pergunta documental e
  identificadores mantidos para auditoria.
- Filtros estruturados separados dos documentais.
- Clientes criados em router, retrieve e generate com conexão de
  até 10 segundos, leitura de até 120 segundos e max_retries=0.
  Esses limites são por chamada, não para o pipeline inteiro.
- Resumo de geração no adaptador identificado como resumo_geracao.
  Mensagem de erro não é considerada resposta documental gerada.
  Tokens não são duplicados nesse resumo.

## Evidência real anterior ao ajuste de timeout
Pergunta:
Quantas contratações têm ano da compra 2026 e o que a Lei
nº 14.133/2021 estabelece sobre o pregão?

Run ID: f49d42a0
Query ID: q_13bffbea

- Contagem correta: 1.234 registros com ano_compra=2026.
- Dense e BM25 receberam somente o pedido sobre a lei.
- Filtros documentais vazios.
- Seleção final: artigos 29, 28 e 6.
- Geração falhou com HTTP 502: timeout do proxy ao conectar ao Ollama.
- Situação: parcial. A resposta combinada completa não foi aprovada.

Log no Drive:
demonstracao_interface_2026-10-14/reserva/COMBINADA_corrigida_f49d42a0.jsonl

## Testes
454 testes passaram com:
`/usr/bin/python3 -m pytest -q --ignore=testes/teste_integracao.py`

Testes de compatibilidade usaram o pacote anterior restaurado,
com 2.125 chunks e índices correspondentes.
git diff --check sem erros.

## Limitações e próximo passo
A decomposição reconhece somente a forma explícita documentada;
não divide perguntas arbitrariamente pela conjunção "e".
Repetir a execução real após estabilização do serviço, com os
novos limites carregados.
Os 2.172 chunks corrigidos ainda precisam de índices próprios confirmados.

## Apoio de IA
IA auxiliou diagnóstico, implementação e testes.
Execuções e conferências realizadas pela integrante responsável.
