# Validação do controle de geração — 19/10/2026

Commit base: `32516f01bf23deaf4ccceb869bc3e1d18eafa27a`, com alterações locais
identificadas por SHA-256 em `evidencias.json`.

## Alterações

- Roteador e gerador solicitam `reasoning_effort=none`.
- `LLM_REASONING_EFFORT` permite configurar o esforço solicitado.
- `ROUTER_MAX_TOKENS` limita a saída do roteador; padrão: 512.
- O limite extrativo existente de 2.048 tokens foi preservado.
- Para ata identificada com menção a PNCP, a recuperação complementa
  a rota estruturada quando há registros dessa natureza no escopo.
- A seleção continua limitada aos documentos vinculados pelo escopo.
- O complemento de rotas é registrado no log de escopo documental.

## Validação

516 testes locais aprovados; 7 deselecionados.
Três execuções reais completas, em processos novos, sem reutilização
de análises ou rankings e com rerank desativado.

| Caso | Run ID | Tempo (s) | Situação |
|---|---|---:|---|
| P03_R | 5ab52cbd | 12.796 | aprovado |
| P04_R | 6b39db30 | 17.167 | aprovado |
| P08_R | e4d3ba8e | 15.277 | aprovado |

P03_R apresentou objeto e número PNCP com suas respectivas fontes.
P04_R apresentou definição, aplicação e exceções do pregão.
P08_R apresentou objeto e contratada em trechos concisos, sem JSON integral.

## Limites

- Os tempos são observações individuais, sem comparação controlada de latência.
- Os diagnósticos alteraram esforço de raciocínio e orçamento de saída;
  não isolam a contribuição de cada parâmetro para os timeouts anteriores.
- As tentativas anteriores com timeout permanecem como histórico.
- Esta rodada não substitui a avaliação completa das personas,
  os casos suplementares ou a reprodução em ambiente independente.
- O texto normativo mantém caracteres de codificação presentes na fonte.
- Não houve reindexação nem regeneração dos embeddings do corpus.
