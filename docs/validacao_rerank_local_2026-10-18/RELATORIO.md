# Validação do rerank local — 18/10/2026

Backend: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1, em CPU.
O backend local foi executado pelo recuperador e confirmado no log,
com preservação dos candidatos, metadados e scores no retorno validado.

## Comparação P08

Foram reutilizados a análise, os artefatos e os resultados das buscas.
Os 24 candidatos de entrada do rerank eram idênticos nas duas execuções.
O cross-encoder pontuou 20 candidatos e preservou quatro sem pontuação.
A comparação inclui as regras finais de seleção da aplicação.

O conjunto final de cinco trechos foi o mesmo. O trecho do objeto
(chunk_3) caiu da posição 1 para 5; o fornecedor (chunk_14) permaneceu
na posição 2. Não foi demonstrada melhora neste caso.

Decisão: manter o backend opcional, desativado por padrão.
São necessárias outras perguntas e anotações de relevância para
avaliar ganho geral. A comparação isolada BM25 versus densa permanece
pendente. Zero chamadas à função busca_bm25 não comprova ausência
da etapa lexical em outro caminho do recuperador.

## Persistência do modelo

O cache com links no Drive apresentou arquivo inválido de 79 bytes.
O modelo carregado foi exportado para arquivos comuns. Os oito arquivos
copiados para o Drive foram conferidos por SHA-256.
Para executar, restaurar a exportação em disco local e configurar
RERANK_MODEL com esse caminho, RERANK_BACKEND=local e
RERANK_ENABLED=true. Não depender do cache com links defeituosos.

## Limites de desempenho

A execução comparativa registrou 31,6 segundos no backend, incluindo
carregamento e inferência. Isso não mede inferência com modelo aquecido.
Os tempos totais das duas consultas não são comparáveis, pois a segunda
reutilizou as buscas.

## Bateria local após a integração

489 testes aprovados, sete testes LLM excluídos, com conexões de rede
bloqueadas no processo de testes. Configuração: RERANK_ENABLED=false
e RAG_DEMO_OFFLINE=false.

Uma execução anterior com RAG_DEMO_OFFLINE=true apresentou quatro
falhas nos testes de interface. A repetição com false passou sem
alterações no adaptador. As duas saídas foram preservadas.

A bateria local não substitui a validação real do modelo, registrada
separadamente em P08.

## Validação final com testes permanentes do backend

497 testes aprovados e sete testes LLM excluídos, com rede bloqueada.
Inclui testes de ordenação, empates, preservação dos candidatos,
fallback por falha de carregamento, scores inválidos e persistência
do score no schema. Versões do ambiente em validacao_final.json.
