# Tratamento de médias sem suporte — 19/10/2026

Pedidos explícitos de médias monetárias podiam chegar à geração documental
sem um executor capaz de realizar o cálculo. No diagnóstico de Marina,
o modelo descreveu compras hospitalares sem responder à pergunta sobre arroz;
a validação bloqueou a saída por ausência de citações.

## Correção

O planejamento reconhece pedidos de cálculo de médias monetárias e informa
a limitação antes de executar busca, cálculo ou geração documental.
Perguntas explicativas permanecem documentais. Os resumos agregados
implementados de P02 e P07 foram preservados nos testes.

O reconhecimento cobre as formulações testadas; não representa compreensão
universal de pedidos de cálculo.

## Validação

- 525 testes locais aprovados; 7 testes LLM deselecionados.
- Validação real pelo adaptador: run `a9fed5c2`.
- Estratégia: esclarecimento; executado: falso.
- Etapas: query_analysis, roteamento e validacao.
- Zero erros; nenhuma busca, consulta de base ou geração documental.
- Tempo observado: 19,894 segundos, sem finalidade de benchmark.

## Pendências

O cálculo de média não foi implementado.
O teste antigo de Marina chama diretamente retrieve e generate, sem passar
pelo planejamento corrigido, e continua pendente de revisão do contrato.
Esta validação não comprova aprovação desse teste nem dos três outros
testes de integração ainda não executados na conferência das seis falhas.
As validações de citações e de proteção de dados não foram removidas.
