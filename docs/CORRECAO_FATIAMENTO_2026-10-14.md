# Correção do fatiamento — 14/10/2026

> Relato histórico de 14/10. O estado dos índices abaixo é daquela data. Para o pacote posterior alinhado, consulte [o guia atual](GUIA_RESTAURACAO_2172.md).


## Problema e correção

A função fatiar_texto encerrava após o primeiro bloco de cada página:
depois de start = end - overlap, a expressão end - start era igual
a overlap, acionando a condição de parada.

A correção percorre o texto inteiro, garante avanço, valida os parâmetros
e preserva caudas curtas.

## Validação local

- 13 testes específicos aprovados.
- Cobertura conferida sobre o texto extraído pelo pypdf.
- Isso não comprova extração perfeita do conteúdo visual dos PDFs.
- Descrição do objeto da ata EBSERH recuperada nos novos chunks.
- Na avaliação lexical com três evidências:
  - P03 selecionou o objeto na ata e o registro PNCP associado.
  - P05 retornou somente a comunicação do processo fictício.
  - P08 selecionou objeto, contratada AGIMED e fabricante TENTE.
- Nenhum modelo foi chamado nessa avaliação.

## Impacto nos artefatos

O conjunto experimental passou de 2.125 para 2.172 chunks:
1.358 estruturados, 217 normativos, 519 agregados e 78 conversacionais.

Comparação por ID:
- 2.098 mantiveram o texto.
- 27 passaram a representar texto diferente.
- 47 IDs novos.
- Nenhum ID removido.

Cache comprovado para o modelo configurado:
- 44 entradas compatíveis por ID, texto e modelo.
- 2.054 textos preservados com modelo histórico não comprovado.
- 27 conteúdos alterados e 47 IDs novos.
- 2.128 entradas pendentes de geração ou comprovação de procedência.

## Estado de utilização

Os artefatos ativos e o pacote anterior foram preservados.
O conjunto experimental ainda não possui FAISS e BM25 alinhados.
Não utilizar seus chunks com os índices antigos.

## Próximas etapas

- Gerar os embeddings pendentes quando o endpoint estiver disponível.
- Reconstruir e auditar FAISS, BM25, IDs e cache em conjunto.
- Revalidar consultas e vínculos no corpus atualizado.
- Atualizar o relatório de recorte e o pacote final.
- Concluir P04 e a avaliação integrada com os modelos reais.
