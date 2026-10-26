# Consulta combinada e encerramentos — 14/10/2026

## Ano da compra e referência legal

- Corrigida a interpretação do ano em referências legais numeradas.
- A Lei 14.133/2021 não transforma a compra de 2026 em intervalo.
- Pedidos reais de dois anos continuam exigindo esclarecimento.
- A pergunta original é preservada para a recuperação documental.

## Conferência na base v3

- Consulta combinada retornou 1.234 contratações com ano da compra 2026.
- Total conferido independentemente na base normalizada.
- Filtro estruturado: ano_compra=2026.
- Recuperação normativa recebeu filtros vazios.
- Rotas fornecidas e recuperação documental simulada.
- Geração final e execução integrada real permanecem pendentes.

## Recusas e esclarecimentos

- P06 recusou a exposição dos dados pessoais solicitados.
- P09 recusou a previsão de valor médio futuro.
- Ambas preservaram query_id e run_id.
- Execução das consultas e chamada ao recuperador foram bloqueadas.
- Adicionado evento de validação com tipo encerramento_consulta.
- Evento registra decisão, motivo e consulta_bases_executada=false.
- Status ok indica execução correta da decisão de encerramento.
- Tokens zero nesse evento não representam o consumo total de uma
  execução anterior do roteador.

## Limitações

- Testes locais não validam a decisão do roteador LLM.
- Respostas reais e logs do fluxo final na interface ainda pendentes.
- Endpoint de modelos indisponível nas tentativas realizadas.
