# Reprodução do commit d31d05a

Commit validado: `d31d05a23bda19d611cfbfce799567ad42483946`.

Clone local independente, ambiente virtual sem pacotes do sistema e restauração do pacote de 2.172 chunks pelo guia, sem reindexação.

## Testes

- Locais sem LLM: 585 aprovados; 7 de integração desmarcados.
- Compatibilidade dos artefatos: 2 aprovados, executados separadamente.
- Integração real: 7 aprovados; um aviso do pytest sobre importação do anyio.

## Conferência manual da interface

- P01 — run `598860d4`: 1.358 registros; filtros corretos; tabela e paginação disponível. Erros registrados: 0.
- P02 — run `c30c9fa6`: 19 itens; 8 homologados; 9 fracassados; 2 desertos; R$ 141.002,08. Erros registrados: 0.
- P04 — run `1ded9042`: Definição, aplicação e exceções; citações aos chunks 28, 29 e 6. Erros registrados: 0.

## Limitações e pendências

- Clone remoto autenticado e reprodução por outro integrante ainda pendentes.
- Estas três consultas não constituem nova rodada completa das personas.
- Rerank desativado nesta reprodução.
- Avaliação das respostas geradas com rerank permanece pendente.

Registros completos: `/content/drive/MyDrive/rag_grande_desafio/reproducao_d31d05a_20261019T183730270236Z`.
