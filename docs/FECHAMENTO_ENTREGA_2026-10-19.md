# Fechamento da entrega — RAG de contratações públicas

Data: 19/10/2026.
Situação: candidata à entrega, com validações e limitações registradas.
O commit definitivo será o commit integrado que contiver este documento.

## Funcionamento entregue

O sistema planeja consultas sobre quatro naturezas de evidência:
estruturada, agregada, normativa e conversacional.

Contagens, listagens e agregações suportadas são executadas sobre os dados
correspondentes, sem usar top_k como limite do cálculo.
Consultas documentais usam recuperação híbrida e respostas com citações.
Pedidos combinados separam o cálculo da resposta documental.
Operações não suportadas recebem esclarecimento ou limitação explícita.

A interface oferece paginação, fontes, evidências, histórico persistido,
feedback e identificação das execuções por run_id e query_id.

## Código, pacote e reprodução

A candidata possui código equivalente ao da reprodução do commit
d31d05a23bda19d611cfbfce799567ad42483946.

Pacote: ENTREGA_EQUIPE_2026-10-16/pacote_v3_2172, na pasta compartilhada.
São 2.172 chunks: 1.358 estruturados, 519 agregados, 217 normativos
e 78 conversacionais.

SHA-256 de data/processed/chunks_teste.json:
dcdcc7a0f8e34da1d0824b5322b6e37306c34e2d53d107c1ca067bc2771c8404

O guia documenta a restauração e a conferência de integridade dos arquivos.
Não é necessário gerar embeddings novamente.

## Validações concluídas e seus escopos

- Reprodução em clone local independente e venv sem pacotes do sistema,
  no mesmo host Colab: 585 testes locais, 2 de compatibilidade e 7 de
  integração real aprovados em execuções separadas.
- Na reprodução, os 7 testes dependentes de rede foram desmarcados na
  execução local e executados separadamente com o serviço real.
- Consultas estruturada, agregada e normativa conferidas na interface
  reproduzida; resultados e identificadores constam no relatório.
- Matriz de 21 casos e avaliação de oito suplementares preservadas com
  os commits efetivamente utilizados. Não constituem uma nova rodada
  integral no commit documental desta entrega.
- Cálculos, paginação e independência do top_k em consulta agregada
  possuem evidências na avaliação da interface.
- Histórico e feedback foram preservados após reinício da aplicação,
  com comparação do registro original e dos logs.
- Comparação de quatro métodos em seis perguntas, incluindo rerank local:
  rankings top_3/top_5 e 24 respostas extrativas com top_k=3.
- A avaliação de respostas foi assistida por IA e não equivale a uma
  avaliação humana independente.

## Decisão sobre rerank

Manter desativado por padrão.
Neste experimento, RRF e RRF com rerank produziram duas respostas completas
em seis perguntas cada. A cobertura média das respostas foi de 63,9% e
61,1%, respectivamente, sem ganho consistente que justifique sua ativação.

As respostas foram geradas sobre rankings preservados, sem resgate
anterior de cobertura. O experimento não substitui a avaliação da interface.
A comparação anterior identificou ganho do rerank na cobertura top_5;
não foram geradas respostas top_5 nesta rodada.

## Limitações conhecidas

- Resultados restritos aos arquivos disponibilizados.
- Ano da compra não equivale a ano de publicação.
- UF da unidade administrativa não define necessariamente o local de execução.
- O cálculo do PCA soma o arquivo integral; o recorte de ano e UF é
  associado à origem do arquivo.
- Médias monetárias e filtros de assinatura não estão implementados.
- Vínculos são verificados por identificadores; resultado vazio não
  comprova inexistência de documentos relacionados.
- O serviço externo pode apresentar demora ou timeout. Um resultado
  correto por fallback não elimina o erro de serviço registrado.
- O histórico é compartilhado entre usuários da mesma instância.
- Reabertura visual do campo de pergunta possui observação pendente na
  validação anterior; a persistência e a resposta original foram conferidas.
- O link público do Gradio é temporário e depende do Colab ativo.

## Pendências externas e complementares

- Reprodução por outro integrante a partir de clone remoto e do guia.
- Identificação do commit, hashes e script da execução do benchmark da
  Janice. Seus arquivos estão preservados como avaliação complementar.
- Ensaio da apresentação, divisão das falas e confirmação de acesso
  aos links da entrega.

Essas pendências devem acompanhar a entrega enquanto não houver evidência
de conclusão. O projeto não deve ser descrito como validado para operações
além das explicitamente suportadas.

## Demonstração e contingência

Demonstrar: listagem P01, cálculo P02, documental P04 e consulta combinada.
Mostrar fontes, filtros, citações, histórico e feedback.

Manter os resultados e logs já registrados disponíveis como alternativa
se o serviço externo estiver indisponível. Ao apresentar registros salvos,
identificá-los como históricos, sem simular uma execução ao vivo.

## Referências

- [restauracao](GUIA_RESTAURACAO_2172.md)
- [reproducao](reproducao_d31d05a_2026-10-19/RELATORIO.md)
- [personas](avaliacao_personas_5499caf_2026-10-19/RELATORIO.md)
- [suplementares](validacao_suplementares_2026-10-19/RELATORIO.md)
- [interface](validacao_interface_fef6d7a_2026-10-19/RELATORIO.md)
- [rankings](comparacao_recuperacao_2026-10-19/RELATORIO.md)
- [respostas](avaliacao_respostas_recuperacao_2026-10-19/RELATORIO.md)
- [janice](avaliacao_complementar_janice_2026-10-19/README.md)
