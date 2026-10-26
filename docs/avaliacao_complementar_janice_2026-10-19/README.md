# Avaliação complementar recebida da Janice

Os cinco arquivos em `originais/` foram preservados sem alterações.
O manifesto de recebimento registra seus hashes e o hash do ZIP.

## Resultado informado
O benchmark registra 9/9 aprovações nos critérios utilizados.
Esse resultado pertence à execução documentada pela Janice.

## Escopo e ressalvas
- O benchmark usa recuperar_evidencias seguido de gerar_resposta.
  Não equivale à reprodução pelo executor atual da interface.
- O pacote não identifica o commit executado, alterações locais
  nem hashes dos artefatos de corpus e índices utilizados.
- O relatório referencia validacao_pipeline_P04_P07_20261019_200245.json,
  que não consta no ZIP recebido.
- Os totais da coluna Fontes devem ser interpretados como entradas
  de evidência/referência, não necessariamente arquivos distintos.
- Contagens e somas podem consultar arquivos completos além do top-k.
  A avaliação deve conferir arquivo, filtros, operação e proveniência;
  fontes fora do top-k não constituem falha automaticamente.
- As observações sobre evidências construídas pelo gerador descrevem
  a execução recebida; sua presença na versão atual exige conferência.

## Pendências para consolidação
Solicitar identificação da versão executada, hashes dos artefatos,
script do benchmark e o arquivo de validação mencionado.
Até esse alinhamento, manter como avaliação complementar, sem substituir
os relatórios versionados de reprodução e da interface.
