# Status do projeto — correções publicadas

## Versão confirmada

- PR: [#52](https://github.com/rag-grande-desafio-grupo1-cenario-1/repositorio1/pull/52).
- Commit das correções: `f3e25d01a8a6fe0c5aac33a86c338346696830cb`.
- Integração na main: `2365d6bb01e937bc02a3e55a2c034eca362a9fe6`.
- Tag anterior preservada: `entrega-2026-10-19`.
- Corpus e índices preservados: 2.172 chunks.

## Validações concluídas

- 754 testes locais aprovados; sete `llm` desmarcados nessa rodada.
- Sete testes de integração real aprovados em execução separada.
- Casos reais de contagem, comparação, tabela, listagem, média, esclarecimento e síntese documental registrados.
- Consultas combinadas com cálculo e documentos separados.
- Persistência de histórico e feedback conferida em processos separados.
- Pergunta e resposta reabertas no histórico, sem tabela duplicada.
- Consulta simples `8474c27d` respondida diretamente com oito itens e conferida no histórico pelo procedimento solicitado.
- Código da main comparado ao commit validado, sem diferenças nos caminhos conferidos.

Os testes e os exemplos comprovam os cenários avaliados. Não garantem resposta correta a qualquer pergunta nem atendimento integral ao enunciado.

## Pendências de engenharia preservadas

- Confirmar publicação da correção de metadados e ampliação das fixtures.
- Adequar coleta integral, idempotência, pausas e falhas por fonte.
- Alinhar manifesto e ingestão quanto a sensibilidade e vigência.
- Centralizar configuração e completar logging dos módulos de preparação.
- Registrar reprodução de versão identificada por outro integrante.
- Identificar versão e artefatos do benchmark complementar da Janice.
- Conferir acessos e acompanhamentos individuais.

A revisão documental não encerra esses itens.
Os casos aprovados não garantem interpretação de qualquer pergunta
nem atendimento integral ao enunciado.

## Referências

- [README](../README.md).
- [Arquitetura](../ARQUITETURA.md).
- [Correções](CORRECOES_RESPOSTAS_2026-10-21.md).
- [Evidências](validacao_respostas_2026-10-21/evidencias.json).
- [Restauração](GUIA_RESTAURACAO_2172.md).

## Reformulações — atualização de 22/10/2026

A rodada final das correções passou com 803 testes locais e sete testes
com o serviço real. O código foi recuperado e os artefatos foram conferidos.
Publicação da branch e inicialização da interface ainda estão pendentes.

Detalhes, limites e evidências:
[Correções das reformulações](CORRECOES_REFORMULACOES_2026-10-22.md).
