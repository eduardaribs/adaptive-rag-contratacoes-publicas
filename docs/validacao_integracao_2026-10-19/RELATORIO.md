# Validação de integração — 19/10/2026

## Resultado

Sete testes de integração reais aprovados em 61,25 segundos.
A bateria local foi executada separadamente com rede bloqueada;
sua saída integral está em `testes_locais.txt`.

## Revisão do contrato

Os testes anteriores de Marina, Rodrigo, fontes e privacidade chamavam
diretamente retrieve e generate, sem o planejamento usado pela interface.

- Marina agora verifica esclarecimento para média monetária sem suporte.
- Rodrigo verifica esclarecimento para filtro de assinatura sem suporte.
- Ambos verificam nos logs ausência de busca e geração documental.
- Fontes verifica uma resposta suportada de P03, exigindo objeto, PNCP,
  fontes correspondentes e citações limitadas aos IDs recuperados.
- Privacidade usa essa mesma execução de P03: comprova CPF no documento
  bruto e sua ausência na resposta e nas evidências apresentadas.
- O compartilhamento de P03 é intencional e não representa duas
  execuções independentes.
- Os testes de consulta normativa, limite top_k e recusa de dados
  bancários/credenciais foram mantidos.

## Limites e histórico

Os resultados anteriores continuam registrados como falhas do contrato
anterior. Esta revisão não implementa cálculo de médias nem filtro de
assinatura e não equivale a responder essas consultas originalmente pedidas.

Os dois testes de compatibilidade de artefatos também passaram na
conferência anterior, usando o pacote de 2.172 chunks.
Isso não comprova a correção do ambiente separado da Janice.

As validações de citações e proteção de dados foram preservadas.
A execução usou o serviço real com rerank desativado.
O aviso PytestAssertRewriteWarning ocorreu na instrumentação do diagnóstico.

Ainda faltam a consolidação da avaliação final das personas e casos
suplementares, revisão documental e reprodução independente da entrega.
