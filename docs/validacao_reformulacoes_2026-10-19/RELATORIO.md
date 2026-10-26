# Reformulações e cobertura documental — 19/10/2026

## Rodada original, commit 5449912

P01_R, P02_R, P05_R, P06_R, P07_R, P09_R e M01_R apresentaram
o conteúdo esperado no adaptador.

P03_R e P08_R tiveram APITimeoutError no roteamento e na geração,
com aproximadamente 120 segundos em cada chamada. Não foram
aprovados nessa execução.

P04_R apresentou aplicação e exceções, mas não a definição.
A regra anterior não reconhecia a reformulação oficial.

## Correções

- Reconhecimento compartilhado das formas normativas suportadas.
- Cobertura de definição na recuperação e seleção da reformulação.
- Cobertura de objeto, PNCP e contratada antes da seleção final,
  usando somente candidatos recuperados no escopo da ata.
- Prioridade dos campos obrigatórios para resistir à reserva multirrota.
- Reconhecimento da expressão número PNCP na seleção factual.
- Recorte conciso da reformulação oficial de objeto e contratada.
- Scores RRF preservados; cobertura registrada separadamente nos logs.
- Pedidos adicionais permanecem fora do recorte restrito.

## Evidências separadas

Replay offline de P03_R, P04_R e P08_R confirmou os campos esperados
nas evidências finais, com rede bloqueada e sem geração.

Geração real sobre o replay:
- P03_R: objeto e PNCP citados, run 04700270.
- P04_R: aplicação, exceções e definição citadas, run 5fd6239b.
- P08_R: campos corretos, mas texto excessivo, run d96a1450.

Após o ajuste de apresentação, os IDs citados na geração anterior
de P08_R foram reapresentados sem nova chamada ao modelo, mostrando
apenas objeto e contratada. Isso não é uma nova integração real.

## Testes e limites

516 testes locais aprovados, sete testes LLM excluídos, rede bloqueada.
Os testes não substituem avaliação das respostas com o serviço.

Execução completa das três reformulações após as correções:
PENDENTE. A rodada original permanece preservada e não foi
substituída pelos resultados isolados.

Limitações conhecidas: redação repetitiva na fonte de P03 e aspas
mal codificadas na fonte normativa. Avaliação geral da recuperação,
casos complementares e reprodução final ainda pendentes.

IA auxiliou diagnóstico, implementação e testes; execuções e
conferências realizadas pela integrante responsável.
