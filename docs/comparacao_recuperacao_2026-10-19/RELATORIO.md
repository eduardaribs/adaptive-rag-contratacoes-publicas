# Comparação de recuperação — 19/10/2026

Seis perguntas documentais; rankings capturados na versão 5499caf.
Pacote de 2.172 chunks. Rerank local dos primeiros 20 candidatos RRF.

| Caso | Vetorial top 3 | BM25 top 3 | RRF top 3 | Rerank top 3 |
| --- | --- | --- | --- | --- |
| P03 | 100.0% | 50.0% | 100.0% | 50.0% |
| P04 | 66.7% | 66.7% | 66.7% | 66.7% |
| P08 | 50.0% | 100.0% | 100.0% | 100.0% |
| P03_R | 50.0% | 0.0% | 0.0% | 50.0% |
| P04_R | 0.0% | 66.7% | 66.7% | 0.0% |
| P08_R | 50.0% | 100.0% | 50.0% | 100.0% |

## Interpretação e limites

- O rerank foi efetivamente aplicado nos seis casos, sem fallback.
- A cobertura usa chunks de referência; não constitui julgamento exaustivo de relevância de todos os candidatos.
- Os rankings reutilizados já estavam sujeitos ao escopo e aos filtros da recuperação original; não são novas buscas globais.
- Os resultados desta comparação não representam a seleção final de evidências após todos os mecanismos de cobertura do pipeline.
- O rerank apresentou ganhos e perdas; permanece opcional e desativado por padrão para a demonstração.
- A primeira latência inclui carregamento do modelo. Os tempos dos demais métodos não foram medidos novamente.
- Não houve geração de novas respostas nesta comparação. A qualidade das respostas com rerank permanece pendente de avaliação.

Evidências completas: `/content/drive/MyDrive/rag_grande_desafio/comparacao_recuperacao_20261019T181107547626Z`.
