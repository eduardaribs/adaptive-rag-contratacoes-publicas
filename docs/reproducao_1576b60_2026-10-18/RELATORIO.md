# Reprodução do commit 1576b60 — 18/10/2026

Foi obtido um clone local independente do commit
`1576b60f4ffc72a22bf614923b39811cfc8fae3f`, previamente confirmado no remoto.
O clone remoto sem credenciais falhou; acesso autenticado por outro integrante
ainda precisa ser verificado.

As dependências foram instaladas em ambiente virtual sem pacotes do sistema.
A criação padrão falhou em ensurepip. Funcionou criar com
`python -m venv --without-pip DESTINO` e instalar com
`python -m pip --python DESTINO/bin/python install -r requirements.txt`.
As versões efetivamente testadas constam em requirements-ambiente-validado.txt.

O pacote de 2.172 chunks foi restaurado sem ingestão ou reindexação.
Os 14 arquivos do manifesto tiveram hashes conferidos antes e depois da cópia.
Passaram 487 testes locais com rede bloqueada e 2 testes de compatibilidade.
Sete testes llm foram excluídos dessa bateria local.

P01, P02 e P04 foram executados com serviço real. Seus resultados e IDs estão
em evidencias.json. A interface foi aberta pelo Python isolado; P04 foi
reaberto pelo histórico com pergunta e resposta originais. O feedback foi
conferido no disco com os mesmos IDs e a fonte normativa.

## Configuração de persistência

Definir explicitamente antes de iniciar o processo:

- PIPELINE_LOG_DIR: pasta de logs da instância.
- HISTORY_PATH: banco SQLite da instância.
- FEEDBACK_PATH: arquivo JSONL de feedback da instância.
- RAG_DEMO_OFFLINE=false para validação real.

Nesta tentativa, FEEDBACK_PATH foi herdado da validação anterior.
O feedback foi salvo corretamente, mas a configuração deve ser explícita
no procedimento entregue.

## Limitações

- Clone remoto autenticado e reprodução por outro integrante pendentes.
- Mesmo host Colab; dependências isoladas não equivalem a máquina nova.
- Rerank desativado; comparação de recuperação não concluída.
- Reinício completo do runtime Colab ainda não validado.
- Aspas mal codificadas no trecho normativo permanecem.
- A versão não está declarada como entrega final congelada.
