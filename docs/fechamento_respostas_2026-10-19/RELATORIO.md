# Fechamento das respostas — 19/10/2026

## Consulta combinada

O roteador podia omitir a base estruturada e encaminhar toda a pergunta
para recuperação documental. O planejamento agora reconhece pedidos
explícitos de contagem/listagem de contratos ou contratações com recorte
de dados, preservando as rotas documentais.

A validação real retornou 1.234 correspondências entre 1.358 registros,
com filtro ano_compra=2026, fonte estruturada e resposta normativa separada.
A parte normativa apresentou definição, aplicação e exceções do pregão.
Run: 5849cfca. Sem erros registrados.

## P05 — marco inicial do prazo

O modelo informou os prazos por item, mas omitiu seu marco inicial.
O complemento conservador usa um trecho literal ligado a dias de uma
única evidência citada. Não escolhe automaticamente entre marcos diferentes.
Perguntas sem os termos reconhecidos ou sem marco explícito são preservadas.

A validação real apresentou papel em 10 dias, canetas em 15 dias,
caráter fictício e marco após a emissão do pedido.
Run: 92506a2e. Citações válidas e complemento registrado no log.

## Validação e limites

539 testes locais aprovados; 7 testes LLM deselecionados.
A consulta combinada foi validada antes da alteração de geração para P05;
os hashes de cada execução estão separados nas evidências.
A versão completa ainda passará pela rodada final das personas.
Não houve regeneração dos embeddings do corpus.

A conferência visual da interface ainda está pendente.
Também permanecem pendentes a avaliação final das personas e casos
suplementares, comparação ampliada de recuperação, revisão documental,
reprodução independente e preparação da entrega.
