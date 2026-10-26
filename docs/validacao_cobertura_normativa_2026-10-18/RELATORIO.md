# Cobertura normativa e consulta combinada — 18/10/2026

## Problema e alteração

A consulta combinada calculava corretamente 1.234 correspondências,
mas a seleção documental apresentou o art. 194, sem relação direta
com o pedido, e omitiu artigos recuperados sobre a aplicação do pregão.

Para a forma geral de pergunta normativa já reconhecida, a seleção
passou a cobrir artigos recuperados que mencionam explicitamente
o assunto. Artigos reconhecidos sem essa menção são removidos da
seleção quando existem artigos com menção direta ao assunto.
Pedidos de artigos específicos e validação de IDs foram preservados.

A regra usa cobertura textual, não comprova relevância semântica geral.
Não acrescenta documentos ou IDs não recuperados.

## Validação

502 testes locais aprovados, sete testes LLM excluídos, rede bloqueada.

Execuções reais com 2.172 chunks e rerank desativado:
- P04, top_k=3: run 582688cb.
- Combinada, top_k=3: run 024cda72.
- Combinada, top_k=5: run a07e2247.

As três respostas apresentaram definição, aplicação e exceções com
citações. As combinadas mantiveram 1.234 correspondências sobre
1.358 registros, com filtro ano_compra=2026 e recorte explícito.

As execuções usaram alterações locais sobre 9e1a268. O hash do código
validado, o hash dos chunks e os resultados estão em evidencias.json.

## Limitações e continuidade

- Aspas mal codificadas no texto da fonte normativa permanecem.
- Esta validação usa o adaptador, não comprova interação visual,
  persistência de histórico ou feedback na versão final.
- Rodada completa P01-P09 e M01 no próximo commit permanece pendente.
- A regra reconhece uma forma específica de pergunta geral; não é
  um solucionador universal de relevância ou de reformulações.

## Apoio de IA

IA auxiliou diagnóstico, implementação e testes.
Execuções e conferências realizadas pela integrante responsável.
