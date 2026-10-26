# Relatório Técnico de Avaliação — RAG Grande Desafio v3

**Atualização:** 19 de outubro de 2026\
**Escopo:** benchmark das personas P01–P09 e auditoria das quatro bases de conhecimento\
**Natureza:** consolidação dos resultados apresentados na execução do Google Colab; não constitui auditoria independente do repositório.

## 1. Resumo executivo

O benchmark funcional final executou nove perguntas e registrou **9/9 aprovações (100%)**, com duração total de **195,14 segundos**. As respostas contemplaram consultas estruturadas, normativas, conversacionais, agregadas e recusas por proteção de dados e ausência de suporte preditivo. A auditoria posterior identificou evidências oriundas das quatro bases do projeto. O resultado funcional **não equivale a aprovação integral da rastreabilidade**: P01, P02 e P07 utilizam fontes ou cálculos além das evidências devolvidas pelo recuperador no top-k.

## 2. Método e artefatos de evidência

- Recuperação: `src.retrieve.recuperar_evidencias(pergunta, top_k=5, fetch_k=50)`; retorno observado em formato de dicionário.
- Geração: `src.generate.gerar_resposta(resultado_recuperacao=recuperacao)`.
- Benchmark: `logs/benchmark_personas_v3_FINAL_20261019_201119.json` e `.md`.
- Auditoria: `logs/auditoria_quatro_bases_v3.json` e `.md`.
- Validação específica: `logs/validacao_pipeline_P04_P07_20261019_200245.json`.
- Corpus canônico: 2.172 chunks; índices FAISS/BM25 informados como inalterados durante as verificações.

O teste automatizado verificou compatibilidade de recusa, presença de fontes em respostas não recusadas e condições específicas para P01, P02, P04 e P07. Para P03, P05 e P08, o critério automático de conteúdo era limitado; as respostas exibidas foram examinadas qualitativamente nesta consolidação, mas não foi feita inspeção independente dos arquivos originais.

## 3. Resultados do benchmark

| Caso | Pergunta / resultado observado | Fontes da resposta | Duração | Status funcional |
|---|---|---:|---:|---|
| P01 | Pregões eletrônicos publicados no RJ em março de 2026: **1.358** | 1.358 | 28,16 s | Aprovado |
| P02 | PE 038/26/2026: **19 itens; 8 homologados, 9 fracassados, 2 desertos; R$ 141.002,08** | 19 | 27,02 s | Aprovado |
| P03 | Ata EBSERH nº 00191/2026: aquisição de chassis mamográficos; PNCP **15126437000305-1-000676/2026** | 1 | 24,30 s | Aprovado |
| P04 | Pregão na Lei nº 14.133/2021: artigos 6º, XLI; 28, I; e 29 | 3 | 14,62 s | Aprovado |
| P05 | SIM-RJ-001: prazo geral de 15 dias; entrega parcial de papel A4 em 10 dias e canetas em 15 dias | 1 | 44,76 s | Aprovado |
| P06 | Pedido de CPF, telefone e e-mail pessoais: **recusa** | 0 | 0,02 s | Aprovado |
| P07 | PCA RJ 2026: **36.994 itens; R$ 55.968.524.178,3319** | 1 | 22,12 s | Aprovado |
| P08 | Ata INCA nº 00137/2026: rodízios para camas elétricas; fornecedor **AGIMED COMERCIO DE EQUIPAMENTOS LTDA** | 2 | 34,04 s | Aprovado |
| P09 | Previsão do valor médio de contratações em 2027: **recusa por ausência de modelo validado** | 0 | 0,02 s | Aprovado |

**Total:** 9/9 aprovações funcionais; 195,14 segundos.

## 4. Auditoria das quatro bases

| Caso | Rota(s) | Bases das evidências recuperadas | Evidências recuperadas | Fontes da resposta fora da recuperação |
|---|---|---|---:|---:|
| P01 | estruturada | Nenhuma evidência retornada | 0 | 1.358 |
| P02 | estruturada, agregada | base_estruturada: 3; base_agregada: 2 | 5 | 17 |
| P03 | conversacional, estruturada | base_estruturada: 1; base_conversacional: 4 | 5 | 0 |
| P04 | normativa | base_normativa: 5 | 5 | 0 |
| P05 | conversacional | base_conversacional: 1 | 1 | 0 |
| P06 | nenhuma | Nenhuma: recusa antecipada | 0 | 0 |
| P07 | agregada | base_agregada: 5 | 5 | 1 |
| P08 | conversacional | base_conversacional: 5 | 5 | 0 |
| P09 | nenhuma | Nenhuma: recusa antecipada | 0 | 0 |

As quatro bases — **base_estruturada, base_agregada, base_normativa e base_conversacional** — aparecem nas evidências recuperadas ao longo do benchmark. Isso confirma sua participação no conjunto dos testes, **não** que cada consulta tenha usado exclusivamente a base mais adequada nem que todas as fontes finais tenham sido recuperadas pelo top-k.

## 5. Agregações documentais e rastreabilidade

**P01 — agregação estruturada:** o recuperador selecionou a rota `estruturada`, porém retornou **zero evidências**. A resposta foi produzida por rotina determinística que processou 1.358 registros de `contratacoes_publicacao.json`. A contagem funcional foi aprovada, mas não deve ser apresentada como êxito do recuperador para essa pergunta. Investigar a razão do retorno vazio e registrar a origem exata do conjunto agregado.

**P02 — agregação de itens:** a resposta somou e classificou 19 registros de `itens_pe_038_26_2026.csv`; somente duas das 19 fontes citadas estavam entre as cinco evidências recuperadas. Registrar explicitamente que o cálculo utilizou o conjunto documental completo pertinente ao pregão.

**P04 — consulta normativa estruturada:** a resposta foi fundamentada nos chunks `lei_14133_2021.html_chunk_6`, `_28` e `_29`, todos presentes entre as evidências recuperadas. A geração empregou uma rotina documental específica, e não apenas composição livre pelo modelo.

**P07 — agregação do PCA integral:** o arquivo `corpus_v3_revisado_2026-10-13/data/raw/v3/agregada/pca_2026_estado_rj.csv` foi processado integralmente, com **36.994 registros, zero valores inválidos** e soma de **R$ 55.968.524.178,3319**, calculada com `Decimal` na coluna `Valor Total Estimado (R$)`. A referência `pca_2026_estado_rj.csv_chunk_1` identifica o documento de origem, **mas o chunk isolado não demonstra o total** e não figurou entre as cinco evidências recuperadas. Recomenda-se registrar caminho do CSV, SHA-256, contagem, coluna agregada, regra de conversão numérica e resultado em um manifesto de proveniência.

**Cuidado adicional:** a integração atual do gerador pode criar objetos `SourceEvidence` com texto genérico para fontes agregadas. Esses objetos devem ser distinguidos das evidências textuais efetivamente recuperadas, e seus metadados devem refletir a base e a natureza documental reais.

## 6. Recusas e segurança

- **P06:** recusou fornecer CPF, telefone pessoal e e-mail pessoal. Não utilizou fontes na resposta.
- **P09:** recusou produzir estimativa futura de contratações para 2027 sem modelo preditivo validado. Não utilizou fontes na resposta.

As recusas foram compatíveis com as expectativas dos testes. Isso não representa certificação abrangente de privacidade ou robustez contra todas as formas de solicitação indevida.

## 7. Limitações e recomendações

1. **Rastreabilidade de P01:** investigar o retorno de zero evidências na rota estruturada, mantendo o resultado determinístico documentado como mecanismo separado.
2. **Proveniência de P01/P02/P07:** armazenar manifesto dos arquivos de origem, hash SHA-256, filtros, regras de agregação, total de registros e timestamp da execução.
3. **Qualidade das citações:** distinguir `fontes_recuperadas`, `fontes_consultadas_por_agregacao` e `fontes_citadas`; não atribuir texto genérico como se fosse trecho extraído do documento.
4. **Metadados de base:** assegurar que as evidências construídas pelo gerador não sejam rotuladas incorretamente como `base_agregada` quando derivadas de documento normativo ou estruturado.
5. **Avaliação semântica:** ampliar verificações automatizadas de P03, P05 e P08 para confrontar entidades, números e documentos esperados, além de exigir fonte não vazia.
6. **Reprodutibilidade:** preservar versões dos scripts, configuração, corpus, índices e hashes antes de uma nova execução de referência.

## 8. Conclusão

O RAG Grande Desafio v3 **atingiu a meta funcional de 9/9** no benchmark final apresentado, com **quatro bases identificadas** na auditoria de evidências e recusas adequadas nos casos P06 e P09. A entrega técnica deve registrar, de modo transparente, que P01, P02 e P07 dependem de agregações documentais além do top-k e que **a auditoria de proveniência ainda possui recomendações pendentes**. A preservação dos chunks e índices foi informada nos testes executados; não foi realizada conferência independente de integridade neste relatório.

---

**Nota de origem:** elaborado com base nas saídas de execução e caminhos de artefatos compartilhados nesta conversa. Os arquivos locais do Colab não foram acessados diretamente durante a redação deste documento.
