# Consultas agregadas

## Implementação

- `src/aggregate_query.py`: leitura dos CSVs e cálculos com Decimal.
- `src/aggregate_planning.py`: reconhecimento conservador das perguntas suportadas.
- `src/query_executor.py`: execução da estratégia consulta_agregada.
- `src/obs.py`: registro da etapa consulta_agregada.

Os cálculos percorrem todos os registros do arquivo selecionado.
Não utilizam busca vetorial nem são limitados por top_k.
Os valores monetários são retornados como strings decimais para preservar a precisão.

## Perguntas validadas

### P02 — itens do pregão

No PE 038/26/2026, quantos itens foram homologados, fracassados e desertos e qual foi a soma dos valores homologados?

Arquivo: `data/raw/v2/agregada/itens_pe_038_26_2026.csv`.

Identificador PNCP presente nos registros:
`42498600000171-1-000757/2026`.

A associação ao nome do processo utiliza o arquivo específico disponibilizado
no corpus; não constitui resolução genérica de números de processos.

Resultado validado:
- 19 itens;
- 8 homologados;
- 9 fracassados;
- 2 desertos;
- valor total homologado: 141002.08;
- nenhum item homologado sem valor.

### P07 — PCA

Quantos itens constam no Plano de Contratações Anual do Estado do Rio de Janeiro para 2026 e qual é o valor total estimado informado?

Arquivo: `data/raw/v2/agregada/pca_2026_estado_rj.csv`.

Resultado validado:
- 36.994 linhas de dados;
- valor total estimado: 55968524178.3319;
- nenhuma linha sem valor estimado.

O arquivo bruto disponível contém os 36.994 registros, embora esteja
armazenado sob raw/v2. A cobertura deste cálculo não deve ser confundida
com a quantidade de linhas anteriormente transformadas em chunks.

A contagem representa linhas do arquivo, não contratações ou fornecedores únicos.
O recorte RJ/2026 é associado à origem do arquivo, não a um filtro aplicado
sobre colunas de UF e ano.

## Validação

- P02 e P07 executados com roteador e executor reais.
- Cálculos conferidos com os resultados esperados das personas.
- Independência de top_k verificada com limites 1, 3 e 5.
- Testes de precisão, zero, ausência, dados inválidos, planejamento,
  execução e observabilidade.
- Suíte sem `testes/teste_integracao.py`: 230 testes aprovados.
- Evento consulta_agregada persistido no JSONL com run_id e query_id.
- O cálculo não consome tokens; o roteamento anterior pode consumir.

## Limitações

- O planejamento reconhece formas específicas das perguntas P02 e P07,
  conforme as expressões de aggregate_planning.py.
- Ainda não há interpretação geral de perguntas agregadas.
- Outros pedidos quantitativos reconhecidos sobre esses documentos
  solicitam esclarecimento em vez de executar um resumo diferente.
- O resumo do PCA ainda não aceita filtros.
- Pedidos documentais abertos permanecem no fluxo híbrido existente.
- A soma informa valores ausentes; ausência não é convertida em zero.
- A integração da apresentação na interface ainda está pendente.
- M01 ainda não combina o cálculo com a verificação de vínculos nas demais fontes.
- A validação acima não inclui a suíte de testes de integração excluída.

## Validação complementar — 07/10/2026

- Suíte local: 288 testes aprovados, excluindo
 `testes/teste_integracao.py`.
- `git diff --check`: sem erros.
- Consulta agregada reutiliza no resultado os mesmos identificadores
 `query_id` e `run_id` registrados no log.
- P02: 19 itens, sendo 8 homologados, 9 fracassados e 2 desertos;
 soma homologada de R$ 141.002,08.
- P07: 36.994 linhas de itens;
 soma estimada de 55968524178.3319, calculada com Decimal.
- M01: verificados 2.125 chunks por ID PNCP completo ou URL específica
 do edital. Encontradas 19 correspondências agregadas e nenhuma
 correspondência complementar por esses identificadores.
 Isso não comprova inexistência de outros vínculos.
- TIC: classificação contextual operacional conectada à consulta,
 com critério, evidência e indicação de casos para revisão.
 Os resultados são propostas, sem validação humana concluída.
- Recuperação: comparação experimental de quatro perguntas mostrou
 vidraçaria e artigo 29 sobre pregão em primeiro lugar, preservou
 artigo 4º em primeiro e melhorou os resultados de elevadores.
- A alternativa foi conectada ao recuperador para rotas exclusivamente
 estruturadas e/ou normativas, mantendo os pesos do RRF.
- A execução posterior pelo recuperador atualizado não foi concluída:
 a chamada de embeddings apresentou timeout em tentativas de
 30 e 60 segundos. Essa validação integrada permanece pendente.
- Nos eventos Dense e BM25 das rotas contextualizadas, a quantidade
 de candidatos representa a seleção dentro das rotas e filtros.

### Pendências

- Repetir a validação real do recuperador atualizado quando o endpoint
 responder.
- Validar filtros documentais em outras rotas e combinações.
- Concluir a revisão humana da classificação TIC com Janice.
- Validar a apresentação dos resultados agregados na interface.
- Executar os testes de integração na versão final.
