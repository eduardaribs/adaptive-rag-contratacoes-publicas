# Correções das reformulações — 22/10/2026

## Problemas corrigidos

- O encaminhamento analítico dependia de verbos específicos e deixava de
  reconhecer pedidos de identificação.
- Listagens de entidades repetiam nomes por registro.
- O planejador misturava campos de fontes diferentes.
- A ausência de um campo opcional provocava uma nova interpretação
  desnecessária e podia alterar a intenção original.
- Referências a pregão eram confundidas com filtros geográficos e temporais.
- Documentos sem vínculo com o pregão podiam entrar como evidências do caso.
- A busca lexical não relacionava formas como homologação e homologar.
- A fusão podia excluir um candidato lexical pertinente; o orçamento
  normativo também impedia preservar trechos complementares.
- A rota agregada, sozinha, autorizava indevidamente o catálogo do PE/PCA
  para perguntas sobre outros conjuntos de dados.

## Comportamento atual

A fonte reconhecida autoriza o caminho analítico; o interpretador escolhe
a operação e a unidade solicitada. Filtros não determinam automaticamente
quais colunas devem aparecer. A listagem distinta considera a combinação
das colunas selecionadas antes do limite de exibição.

Campos indisponíveis continuam bloqueados. O erro identifica tarefa,
fonte, campos inválidos e campos permitidos para orientar a retentativa.
O campo opcional pedido_documental assume null quando omitido.

O escopo de pregão preserva normas como fundamento geral e exige referência
exata nas demais fontes. Isso não comprova fatos específicos do procedimento.

A normalização lexical preserva acentos até o stemming em português.
A cobertura entre métodos é aplicada somente com escopo documental,
candidatos finais exclusivamente normativos e sem rerank aplicado.
O orçamento normativo padrão é de 6.000 caracteres; a variável
NORMATIVE_CONTEXT_MAX_CHARS pode substituí-lo.

## Validação final

- 803 testes locais aprovados em 14,91 segundos.
- 7 testes com o serviço real aprovados em 49,94 segundos.
- git diff --check aprovado.
- Corpus e índices recuperados do pacote preservado, sem regeneração.
- Evidências: validacao_reformulacoes_2026-10-22/.

Durante as correções, foram conferidos a identificação dos oito itens
homologados, os três fornecedores sem repetição, a explicação documental
de homologação e a combinação de contagem com explicação sobre pregão.

As rodadas anteriores com falhas permanecem registradas. Os resultados
demonstram os casos e contratos exercitados, não acerto universal para
qualquer pergunta. Citações reconhecidas não equivalem, por si só,
a uma verificação semântica de cada afirmação.

## Publicação e interface

Esta documentação é preparada na branch de recuperação. Publicação,
integração na main e inicialização da interface devem ser registradas
após sua conclusão. O histórico persistido no Drive deve ser preservado.
