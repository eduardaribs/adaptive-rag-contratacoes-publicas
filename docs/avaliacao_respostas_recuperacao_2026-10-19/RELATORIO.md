# Avaliação de respostas por método de recuperação

24 gerações extrativas reais: seis perguntas e quatro métodos, top_k=3.
Foram reutilizados rankings preservados; não houve nova busca ou rerank.
A seleção de cobertura anterior à geração não foi aplicada.

## Resultados

| Método | Cobertura média na resposta | Completas |
|---|---:|---:|
| vetorial | 44.4% | 0/6 |
| bm25 | 63.9% | 2/6 |
| rrf | 63.9% | 2/6 |
| rrf_rerank | 61.1% | 2/6 |

## Interpretação e decisão

- Manter rerank desativado por padrão: dois ganhos, duas perdas e dois empates frente ao RRF em cobertura da resposta.
- O custo do rerank foi medido na comparação anterior; os tempos desta rodada representam geração e validação, não o pipeline completo.
- 23/24 respostas apresentaram citações pertencentes à entrada.
- P04_R vetorial registrou erro de validação: 'Selecione entre um e cinco chunks.' O resultado foi preservado.
- Citação válida não comprova pertinência ou completude.
- P03 vetorial omitiu o objeto apesar de haver evidência na entrada.
- Para P08, 'rodízio com freio' sem explicitar camas elétricas foi considerado cobertura incompleta do objeto.
- Para P04, definição inclui obrigatoriedade para bens e serviços comuns e critérios de julgamento; citar apenas o art. 29 é parcial.

## Limites

- Revisão assistida por IA, sem avaliação humana independente.
- Uma geração por combinação; sem repetições ou inferência estatística.
- Não avalia respostas com top_k=5.
- Os rankings originais já possuem o escopo e filtros da recuperação registrada; não é uma comparação global irrestrita dos métodos.
- Não substitui a avaliação da interface com seleção de cobertura.
- Os resultados anteriores de top_k=5 continuam restritos aos rankings.
