# Validação offline da geração e consultas — 13/10/2026

## Alterações

- Separado o prompt de seleção extrativa do prompt de resposta livre.
- Preservada a exigência de IDs exatos dos chunks recuperados.
- Mantidos os bloqueios de seleções inválidas e citações inválidas.
- Acrescentadas regras gerais para distinguir fornecedor, contratada,
  fabricante e marca, preservar prazos por item, entregas parciais
  e identificar conteúdo fictício.
- Limitadas afirmações de ausência aos trechos disponíveis.

## Testes offline

- 53 testes de geração, citações, seleção extrativa e escopo aprovados.
- 85 testes relacionados a planejamento, filtros, combinação e TIC
  aprovados.
- Respostas do modelo simuladas nos testes de geração.
- Não foi comprovada a eficácia dos prompts com o modelo real.

## Fontes conferidas no pacote revisado

- P03: ata_00191.pdf e vínculo pelo processo 23877002295202692
  com PNCP 15126437000305-1-000676/2026.
- P08: objeto no chunk 1, contratada AGIMED no chunk 6
  e fabricante/marca TENTE no chunk 2 de ata_00137.pdf.
- P05: comunicação fictícia contém papel A4 em 10 dias,
  canetas em 15 dias e entregas parciais.
- Essa conferência verifica a disponibilidade das fontes,
  não o ranking nem a resposta produzida pelo modelo.

## Cálculos locais

- P02: 19 itens, 8 homologados, 9 fracassados, 2 desertos;
  soma homologada 141002.08.
- P07: 36.994 linhas; soma estimada 55968524178.3319.
- M01: 2.125 chunks verificados, 19 correspondências agregadas
  e zero vínculos complementares pelos identificadores pesquisados.
- Resultados invariáveis com top_k 1, 3 e 5 no executor.
- Planos fornecidos diretamente, sem roteamento pelo modelo.
- Ausência de vínculo por identificadores não comprova ausência
  de documentos relacionados por conteúdo ou outros processos.

## Pendências

- Revalidar P03, P08 e P05 com o endpoint disponível.
- Executar P01–P09 e M01 no fluxo completo da versão integrada.
- Avaliar relevância, completude e suporte das afirmações.
- Verificar disponibilidade do rerank e executar a comparação
  entre configurações de recuperação.
- Repetir a avaliação da recuperação após regenerar os embeddings.

## Artefatos utilizados

- Pacote: corpus_v3_revisado_2026-10-13.
- SHA-256 do ZIP:
  e069a9f03e7d219250dafda94c2bd47483aea24a9bb5f66c016f9e0d9b32f714.
- Modelo não comprovado para 2.081 vetores históricos.
- Regeneração bloqueada por ConnectTimeout no endpoint.

## Resultado da suíte geral

- 363 testes aprovados em 6,81 segundos.
- Excluído: `testes/teste_integracao.py`.
- Compatibilidade conferida com os artefatos revisados do Drive.
- `git diff --check` aprovado.
