# Comparação de recuperação — P08

Pergunta: O que a ata nº 00137/2026 do INCA informa sobre o objeto
adquirido e o fornecedor?

Foram identificados trechos sobre o objeto em ata_00137.pdf_chunk_3
e sobre o fornecedor em ata_00137.pdf_chunk_14.
Esses são trechos verificados, não uma anotação exaustiva de relevância.

| Método | Posição do chunk_3 | Posição do chunk_14 |
|---|---:|---:|
| Densa filtrada | 1 | 3 |
| BM25 contextual | 3 | 2 |
| RRF puro | 1 | 2 |
| RRF com seleção final | 1 | 2 |
| Cross-encoder com seleção final | 5 | 2 |

## Procedimento

A busca densa salva foi reutilizada. O BM25 contextual foi recalculado
sobre os mesmos artefatos. Os rankings foram capturados após os filtros
e antes da fusão. O baseline final foi reproduzido com rede bloqueada,
sem novos embeddings ou inferência cross-encoder.

Na comparação anterior RRF versus cross-encoder, a igualdade dos
24 candidatos de entrada foi verificada. O cross-encoder pontuou
20 candidatos e preservou quatro sem score.

Correção de descrição do protocolo anterior: apenas a busca densa foi
reutilizada; o BM25 contextual foi recalculado, pois não passa pela
função busca_bm25 interceptada naquele experimento.

## Resultado e decisão

O RRF colocou os dois trechos verificados nas primeiras duas posições.
O cross-encoder manteve o mesmo conjunto final de cinco trechos,
mas deslocou o trecho do objeto da primeira para a quinta posição.

Manter RERANK_ENABLED=false por padrão, com backend local opcional.
Não foi demonstrado ganho do rerank em P08.

## Limitações

Um único caso, sem relevância anotada de forma exaustiva e sem métricas
gerais de recuperação. Não permite concluir superioridade global de
qualquer método nem comparar latências reais entre eles.
