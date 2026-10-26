# Corpus Inventory

## Pacote de execução conferido em 19/10/2026

O corpus bruto v3 possui oito arquivos. O pacote posterior à correção do
fatiamento possui 2.172 chunks e índices alinhados.

Distribuição e metadados medidos:
[Auditoria do pacote](docs/AUDITORIA_PACOTE_2172_2026-10-19.json).

Os cálculos usam os CSV completos, não apenas os 519 chunks agregados.
O PCA disponibilizado contém 36.994 linhas; o recorte de ano e UF está
associado à origem da exportação recebida da equipe.

O controle PNCP da contratação EBSERH é
`15126437000305-1-000676/2026`. O identificador com sufixo `-000001`
documentado abaixo identifica a ata, não o campo de controle da contratação.

UF identifica a unidade administrativa, não necessariamente a execução.
Ano da compra, publicação e vigência são distintos. Campos previstos
no manifesto não comprovam preenchimento nos chunks.

Metadados vazios não demonstram ausência da informação no texto original.
A auditoria registra campos vazios sem preencher valores por suposição.

Restauração e limitações: [guia atual](docs/GUIA_RESTAURACAO_2172.md).


## Estado atual do corpus

- **Cenário:** Contratações Públicas do Estado do Rio de Janeiro
- **Versão atual:** v3
- **Arquivos inventariados:** 8
- **Falhas de integridade:** 0
- **Corpus v2:** preservado como snapshot congelado
- **Corpus v3:** versão atual após nova reconstrução da base estruturada pelo PNCP

---

## Base estruturada — PNCP

### Identificação

- **Cenário:** Contratações Públicas do Estado do Rio de Janeiro
- **Base:** Estruturada
- **Fonte:** Portal Nacional de Contratações Públicas (PNCP)
- **API:** Consulta PNCP
- **Endpoint:** `/v1/contratacoes/publicacao`
- **UF:** RJ
- **Modalidade:** 6 — Pregão Eletrônico
- **Período consultado:** 01/03/2026 a 31/03/2026
- **Total de registros:** 1.358
- **Registros duplicados:** 0

### Integridade

- **Primeira publicação encontrada:** 02/03/2026 07:00:59
- **Última publicação encontrada:** 31/03/2026 16:54:47
- **IDs PNCP encontrados:** 1.358
- **IDs PNCP únicos:** 1.358
- **UFs encontradas:** RJ
- **Modalidades encontradas:** 6
- **SHA-256:** `681a935887201bf87073c0bc80979a388929adcc45f9de86e332e2e23cab565e`

### Dados brutos

`data/raw/v3/estruturada/pncp/rj/pregao_eletronico/2026-03/contratacoes_publicacao.json`

### Principais informações disponíveis

Os registros incluem informações como:

- órgão/entidade;
- CNPJ do órgão;
- unidade administrativa;
- município;
- objeto da contratação;
- modalidade;
- número da compra;
- número de controle PNCP;
- valores estimado e homologado;
- datas de publicação e atualização;
- situação da contratação;
- demais informações disponíveis no retorno da API.

### Versionamento

A reconstrução online realizada em 25/09/2026 produziu 1.358 registros.

A comparação com o snapshot v2 identificou 1.314 registros idênticos e 44 registros com alterações na fonte.

A v2 foi preservada e a nova coleta originou a v3.

---

## Base normativa — Lei 14.133/2021

### Identificação

- **Base:** Normativa
- **Documento:** Lei nº 14.133, de 1º de abril de 2021
- **Título:** Lei de Licitações e Contratos Administrativos
- **Fonte:** Presidência da República — Planalto
- **Formato:** HTML
- **Arquivo:** `data/raw/v3/normativa/federal/lei_14133_2021/lei_14133_2021.html`
- **SHA-256:** `b5ea9780f22f4381887c1c1f341e8edb945f50b37010f78f27ade544b3d308f2`

### Verificação

- **Status HTTP na coleta:** 200
- **Tamanho:** 649.705 bytes
- **Texto extraído:** 289.010 caracteres
- **Identificação do documento:** confirmada

### Observação

O documento foi obtido da fonte oficial do Governo Federal. A redação vigente deve ser conferida na fonte oficial quando a resposta depender de vigência normativa.

---

## Base conversacional — Atas de Registro de Preços

A v3 contém três atas oficiais provenientes do PNCP.

### Ata FIOCRUZ nº 00001

- **Órgão:** Fundação Oswaldo Cruz — INCQS/FIOCRUZ
- **Ano/sequencial:** 2026 / 227
- **Objeto:** Aquisição de materiais da marca AGILENT
- **Formato:** PDF
- **Páginas:** 8
- **Arquivo:** `data/raw/v3/conversacional/atas/fiocruz/2026/ata_00001.pdf`
- **SHA-256:** `3372ad5388cb87cc0fdd0d604fdc82f343b0c55d3f97b1d295ec56c3004dfb2a`

### Ata Ministério da Saúde/INCA nº 00137/2026

- **Órgão:** Ministério da Saúde — Instituto Nacional de Câncer (INCA)
- **CNPJ:** 00.394.544/0001-85
- **Ano/sequencial:** 2026 / 359
- **Objeto:** Aquisição de rodízios para camas elétricas Stryker
- **Formato:** PDF
- **Páginas:** 10
- **Arquivo:** `data/raw/v3/conversacional/atas/ministerio_saude/2026/ata_00137.pdf`
- **SHA-256:** `ca206d7d30d9dff83c22e272e34f2884046c589a78c5dbf40e94f6e9e96029d7`

### Ata EBSERH nº 00191/2026

- **Órgão:** Empresa Brasileira de Serviços Hospitalares (EBSERH)
- **Unidade:** Complexo Hospitalar da Universidade Federal do Rio de Janeiro (CH-UFRJ)
- **CNPJ:** 15.126.437/0003-05
- **Ano/sequencial:** 2026 / 676
- **Número de controle PNCP:** `15126437000305-1-000676/2026-000001`
- **Objeto:** Aquisição de produtos para saúde — peças para mamógrafos (chassis)
- **Formato:** PDF
- **Páginas:** 12
- **Arquivo:** `data/raw/v3/conversacional/atas/ebserh/2026/ata_00191.pdf`
- **SHA-256:** `53c2ead7aa1f9d72b0845f773dab8ea6c2d7bf546ca4dbdd9e9c1612c834762a`

### Sensibilidade

As atas podem conter nomes, identificadores funcionais e dados de contato de pessoas físicas.

Esses dados devem ser tratados conforme as regras de sensibilidade e guardrails do projeto, evitando exposição desnecessária nas respostas do RAG.

---

## Base conversacional — Comunicações sintéticas

### Identificação

- **Natureza:** conteúdo inteiramente fictício para testes
- **Fonte:** simulação criada pela equipe com apoio de IA
- **Processo fictício:** SIM-RJ-001
- **Quantidade de mensagens:** 3
- **Formato:** TXT
- **Arquivo:** `data/raw/v3/conversacional/comunicacoes_sinteticas/troca_mensagens_material_escritorio_001.txt`
- **SHA-256:** `23cd93d88c48397746b1aa0558b18dab0c54687c66be73034d1925e5abd92c65`

### Uso e limitações

O conteúdo não representa comunicação pública real e nunca deve ser apresentado pelo RAG como evidência de uma contratação real.

---

## Base agregada — Plano de Contratações Anual (PCA) 2026

### Identificação

- **Base:** Agregada
- **Fonte:** Portal Nacional de Contratações Públicas (PNCP)
- **Órgão:** Estado do Rio de Janeiro
- **CNPJ:** 42.498.600/0001-71
- **Ano:** 2026
- **Formato:** CSV
- **Quantidade de itens:** 36.994
- **Valor total estimado informado na fonte:** R$ 55.968.524.178,3319
- **Arquivo:** `data/raw/v3/agregada/pca_2026_estado_rj.csv`
- **SHA-256:** `2a8e6b3bb939fb0b281fce69b8b2f077f36d77ee319f16dd632b64dca27ab75e`

### Verificação

- **Tamanho:** 14.469.918 bytes
- **Separador:** ponto e vírgula (`;`)
- **Quantidade de colunas:** 20
- **Linhas de dados:** 36.994

---

## Base agregada — Valores homologados por item

### Identificação

- **Fonte:** Portal Nacional de Contratações Públicas (PNCP)
- **Órgão:** Estado do Rio de Janeiro — Fundo Estadual de Saúde
- **ID PNCP:** `42498600000171-1-000757/2026`
- **Edital:** PE 038/26/2026
- **Data dos resultados de homologação informados:** 18/09/2026

### Dados

- **Total de itens:** 19
- **Itens homologados:** 8
- **Itens fracassados:** 9
- **Itens desertos:** 2
- **Soma dos valores homologados:** R$ 141.002,08
- **Arquivo:** `data/raw/v3/agregada/itens_pe_038_26_2026.csv`
- **SHA-256:** `1a52fcc125c9d5793263339f7570d21999262e8b239fd8fd80a77e6b616daba2`

Os itens fracassados e desertos permanecem sem valor homologado, em vez de serem representados artificialmente como valor zero.

Esta coleta representa uma contratação específica e não deve ser interpretada como cobertura de todas as contratações do Estado do Rio de Janeiro.

---

## Resumo de integridade da v3

A versão v3 possui:

- **8 arquivos**
- **0 falhas**
- **1 arquivo estruturado JSON**
- **1 documento normativo HTML**
- **3 atas PDF**
- **1 comunicação sintética TXT**
- **2 arquivos agregados CSV**

O snapshot v2 permanece preservado. A v3 representa o estado mais recente documentado do corpus e não deve sobrescrever retroativamente versões anteriores.
