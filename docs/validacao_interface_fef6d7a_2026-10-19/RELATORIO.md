# Validação da interface — 19/10/2026

Aplicação no commit fef6d7a, com pacote de 2.172 chunks.

- P02, P07 e M01: conteúdo e apresentação conferidos.
- Paginação: tabelas e filtros preservados; navegação sem novo roteamento, busca ou geração.
- P02 com top_k=1: mesmos cálculos da execução com top_k=3.
- Feedback: pergunta, comentário, fontes e IDs persistidos.
- Histórico: resultado preservado após reinício; logs idênticos.

## Limitações e ocorrências

- Conferência visual relatada pela usuária.
- P02 apresentou os mesmos cálculos com top_k=3 e top_k=1.
- A execução f40f100c teve timeout no roteamento; o cálculo agregado foi concluído corretamente.
- O prefixo '1. ' na pergunta levou a esclarecimento; limitação de reconhecimento registrada.
- O navegador apresentou timeout no JavaScript externo da Gradio. Foi testado um ajuste de template apenas no processo.
- Resta confirmar visualmente a restauração da pergunta na caixa de entrada; resultado e feedback persistidos foram verificados.
