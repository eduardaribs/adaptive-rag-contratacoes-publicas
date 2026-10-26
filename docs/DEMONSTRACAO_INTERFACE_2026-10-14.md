# Demonstração da interface — 14/10/2026

## Escopo
Modo offline opcional, ativado por `RAG_DEMO_OFFLINE=true`.
Aceita as três perguntas apresentadas nos exemplos: P02, P07 e M01.
Utiliza planos locais predefinidos e executa cálculos reais nos arquivos.
Não executa roteador LLM, recuperação vetorial, rerank ou geração.
Pedidos adicionais recebem esclarecimento, sem descartar critérios.

## Execução visual conferida
| Caso | Resultado | Run ID | Query ID |
|---|---|---|---|
| P02 | 19 itens; 8 homologados; 9 fracassados; 2 desertos; R$ 141.002,08 | a8abc21b | q_demo_138ea1b3 |
| P07 | 36.994 linhas; R$ 55.968.524.178,3319 estimados | b6e75cd3 | q_demo_ed2297c7 |
| M01 | Mesmo resumo de P02; 2.172 chunks verificados; 19 correspondências agregadas e zero nas demais naturezas | cab7b95c | q_demo_7c0c11d6 |

P07 apresenta o recorte associado à fonte; não representa despesa realizada.
M01 verifica ID PNCP completo ou URL específica do edital.
Ausência de vínculo por identificador não comprova inexistência de documentos relacionados.

## Feedback
Feedback de M01 salvo no Drive e conferido:
pergunta, avaliação, comentário, fonte, query_id e run_id preservados.
Arquivo: `demonstracao_interface_2026-10-14/feedback.jsonl`.

## Validação técnica
- 29 testes específicos da interface e demonstração passaram.
- 442 testes passaram excluindo integração e compatibilidade de artefatos.
- 2 testes de compatibilidade passaram separadamente no pacote anterior.
- `git diff --check` sem erros.
- Os testes específicos usam executor simulado; os cálculos reais foram conferidos visualmente.

## Versões
Commit base: `13c35f3aeb07168e0ca754e23f63cc2084cb7cd9`.
Código da demonstração: commit que incorpora este documento.
CSV: pacote `corpus_v3_revisado_2026-10-13`.
M01: chunks corrigidos de `validacao_fatiamento_20261014_131813_311268`.
Índices conferidos: pacote anterior, com 2.125 chunks.
A compatibilidade desses índices não valida o corpus corrigido de 2.172 chunks.

## Inicialização no Colab
Antes de importar a interface, configurar:
- `RAG_DEMO_OFFLINE=true`
- `RAG_DEMO_PACOTE`: caminho absoluto do pacote com os CSV v3.
- `RAG_DEMO_CHUNKS`: caminho absoluto dos chunks corrigidos.
- `RAG_DEMO_COMMIT`: hash do código utilizado na demonstração.
- `FEEDBACK_PATH`: caminho persistente do JSONL de feedback.

Executar a interface a partir da raiz do repositório.
Para o fluxo normal, desativar `RAG_DEMO_OFFLINE` e reiniciar a interface.

## Pendências
Geração documental e roteamento LLM reais; comparação com rerank;
embeddings e índices do corpus corrigido; histórico persistente de consultas;
demais casos da interface e integração na main.

## Apoio de IA
IA utilizada para auxiliar implementação, testes e documentação.
Execuções e conferência visual realizadas pela integrante responsável.
