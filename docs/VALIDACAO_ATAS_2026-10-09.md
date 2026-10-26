# Validação das consultas a atas — 09/10/2026

## Alterações

- Tratamento de ano vazio como metadado ausente na recuperação.
- Identificação de atas pelo número e ano presentes no conteúdo.
- Restrição dos candidatos ao documento identificado.
- Vínculo estruturado por correspondência exata do número de processo.
- Uso de resposta extrativa para consultas a atas identificadas.
- Preservação da sanitização e das validações de citações.

## Validação disponível

A suíte apresentou 347 testes aprovados após o ajuste de escopo.
As alterações posteriores de geração precisam ter seus resultados
de teste conferidos antes da integração.

### P08

A execução apresentou o objeto e a contratada por trechos citados:
aquisição de rodízios para camas elétricas e AGIMED COMERCIO DE
EQUIPAMENTOS LTDA.

- Run ID: 1e68c252
- Query ID: q_5b36b586
- Resposta extrativa; apresentação extensa permanece como melhoria.

### P03

A recuperação localizou a ata 00191 e o registro PNCP
15126437000305-1-000676/2026 por processo exato.

A resposta final permanece bloqueada pela validação extrativa.

- Último Run ID: c2639b97
- Último Query ID: q_b4ade8d2
- Execução anterior retornou posições numéricas em vez de Chunk IDs.
- A causa da última rejeição ainda precisa ser conferida no log.

## Pendências antes de integrar

- Corrigir e repetir P03.
- Adicionar teste da ativação automática do modo extrativo para atas.
- Revalidar P08 após o último ajuste do prompt.
- Conferir regressões e registrar os resultados finais.

Este registro não representa aprovação completa das personas.
