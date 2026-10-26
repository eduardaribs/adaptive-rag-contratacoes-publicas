# Escopo documental e candidato lexical único — 13/10/2026

## Alterações

- Reconhecimento de processo alfanumérico explícito na pergunta.
- Correspondência exata do identificador em fontes conversacionais.
- Preservação das partes da fonte localizada de forma unívoca.
- Escopo vazio quando o processo não é encontrado ou é ambíguo.
- Preservação do escopo anterior para atas.
- Candidato lexical único com termos compartilhados pode ser retornado
  mesmo com score BM25 não positivo, mantendo a pontuação original.
- Ausência de correspondência lexical continua sem resultado.

## Conferência local

P05 foi limitado à comunicação do processo fictício SIM-RJ-001.
O conjunto tinha um candidato, com correspondência lexical e score
BM25 negativo. Após a correção, esse candidato foi retornado.
Nenhuma chamada aos modelos ou alteração dos artefatos foi realizada.

## Pendências

- Validar o escopo no fluxo híbrido completo com os modelos reais.
- Validar a resposta de P05: prazos por item, entregas parciais,
  início dos prazos e identificação explícita do conteúdo fictício.
- P04: artigo 6º presente, com aproximadamente 23 mil caracteres;
  ficou fora dos três primeiros resultados na avaliação lexical.
  A seleção da definição de pregão ainda precisa ser investigada.
- P03: melhorar a seleção documental, reduzindo trechos genéricos.
- Executar a avaliação final das personas na interface.
