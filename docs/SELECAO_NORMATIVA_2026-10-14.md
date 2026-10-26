# Cobertura de definição normativa — 14/10/2026

## Comportamento

Em perguntas gerais no formato 'o que ... estabelece sobre ...',
reserva uma vaga para uma definição textual do assunto,
quando essa definição já está entre os candidatos recuperados.

Restrições:
- Recuperação exclusivamente normativa.
- Pelo menos duas vagas.
- Sem solicitação explícita de artigo.
- Não acrescenta candidatos externos ao ranking.
- Preserva scores, textos, IDs e ordem relativa dos selecionados.

A política é uma heurística de cobertura de conteúdo.
Não equivale a rerank semântico nem garante completude.

## Validação

- P04 lexical selecionou os artigos 29, 28 e 6.
- Artigos identificados pelo conteúdo, não pelo número do chunk.
- Testes cobrem outras modalidades e pedidos específicos.
- Testes cobrem definição ausente ou fora dos candidatos.
- Integração offline e eventos JSONL conferidos.
- Logs registram política, aplicação e IDs antes/depois.
- rerank_applied permanece false.

## Limitações

- Geração real e avaliação híbrida real pendentes.
- Artigo 6º permanece longo; orçamento de contexto pendente.
- Concorrência, contratação direta e fiscalização ainda
  apresentam problemas de relevância não resolvidos pela política.
- Experiências com janelas, unidades normativas, b=0 e
  expansão manual não foram incorporadas ao código.

## Conferência do contexto de P04

- Artigo 29: 585 caracteres.
- Artigo 28: 467 caracteres.
- Artigo 6º: 23.026 caracteres.
- Contexto montado: 24.418 caracteres e 3.379 palavras.
- Textos completos e IDs preservados.
- Nenhuma chamada ao modelo realizada.
- Caracteres e palavras não equivalem aos tokens do modelo.
- Aceitação pelo servidor e qualidade da resposta ainda pendentes.
- O modo extrativo atual apresenta chunks inteiros;
  concisão da resposta ainda precisa ser avaliada.
