# Intenção documental explícita — 19/10/2026

P01 foi encaminhada indevidamente como consulta combinada porque o roteador
incluiu a base normativa. A listagem foi calculada, mas uma tarefa documental
não solicitada foi executada e terminou em erro de seleção extrativa.

O planejamento agora exige um segundo pedido documental explícito para
combinar contagem/listagem com recuperação documental. Rotas sugeridas pelo
LLM não criam, sozinhas, uma tarefa adicional para o usuário.

A decomposição reconhece as formulações testadas de segundo pedido sobre
lei, decreto, resolução, portaria, norma, regra, atas ou comunicações.
Não interpreta apenas a modalidade pregão ou campos de exibição como
pedido documental. Esse reconhecimento é limitado às formas implementadas.

## Validação

- 552 testes locais aprovados; 7 testes LLM deselecionados.
- P01, run bbae7b28: consulta estruturada, 1.358 registros, sem recuperação
  ou geração documental; zero erros.
- Combinada, run 8c463f49: 1.234 correspondências, filtro ano_compra=2026
  e resposta normativa separada; zero erros.
- Testes incluem rotas documentais indevidas em P01 e pedidos combinados reais.
- A primeira execução local identificou ausência do reconhecimento de Decreto;
  a falha e sua correção foram preservadas no backup.

## Pendências

A rodada iniciada no commit 5c77133 ficou suspensa em P01 e permanece
histórica. A avaliação final de todas as personas precisa usar a nova versão.
A conferência de interface de P05 e combinada no commit anterior está
registrada separadamente, com seus próprios run IDs.
