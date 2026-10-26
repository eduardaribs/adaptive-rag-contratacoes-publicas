"""Interpretação de perguntas em planos analíticos validados."""

import json
import os
import uuid

from openai import OpenAI
from pydantic import model_validator
from typing import Literal

from src import obs
from src.analytical_plan import Contrato, CAMPOS, PlanoAnalitico


class InterpretacaoAnalitica(Contrato):
    tipo: Literal["plano", "esclarecimento", "documental"]
    mensagem: str
    plano: PlanoAnalitico | None
    pedido_documental: str | None

    @model_validator(mode="after")
    def validar_decisao(self):
        if self.tipo == "plano":
            if self.plano is None:
                raise ValueError("Decisão de execução exige plano.")
            if self.plano.filtros:
                raise ValueError(
                    "O interpretador exige filtros dentro de cada tarefa."
                )
            if self.plano.pendencias:
                raise ValueError("Plano com pendências não pode ser executado.")
        else:
            if self.plano is not None:
                raise ValueError("Decisão sem execução não deve fornecer plano.")
            if not self.mensagem.strip():
                raise ValueError("Decisão sem execução exige explicação.")
        return self


CATALOGO = {
    "itens_pe": {
        "descricao": (
            "Itens do arquivo do PE 038/26/2026. "
            "Permite consultar situação dos itens e valores homologados."
        ),
        "processo": "PE 038/26/2026",
        "id_contratacao_pncp": "42498600000171-1-000757/2026",
        "situacoes": ["homologado", "fracassado", "deserto"],
        "campos": CAMPOS["itens_pe"],
        "limites": (
            "Não contém data de assinatura, valores estimados, "
            "comprovação de entrega ou pagamento."
        ),
    },
    "pca": {
        "descricao": (
            "Arquivo disponibilizado como PCA do Estado do RJ para 2026. "
            "Contém planejamento, não contratações efetivadas."
        ),
        "campos": CAMPOS["pca"],
        "limites": (
            "UF e ano estão associados à origem do arquivo; "
            "não são colunas para filtrar suas linhas."
        ),
    },
}

CATALOGO["itens_pe"]["semantica"] = {
    "numero_item": "Identificador do item, não quantidade física.",
    "quantidade_homologada": (
        "Quantidade física do produto na linha. Não conta itens. "
        "A compatibilidade de unidades entre produtos não está comprovada."
    ),
    "valor_unitario_homologado": "Preço homologado por unidade do produto.",
    "valor_total_homologado": "Valor homologado total do item.",
    "situacao_item": "Situação do item: homologado, fracassado ou deserto.",
}


CATALOGO["itens_pe"]["unidades_de_resultado"] = {
    "item": {"campos_identificadores": ["numero_item"]},
    "fornecedor": {"campos_identificadores": ["fornecedor"]},
}
CATALOGO["itens_pe"]["campos_ausentes"] = ["descricao"]
CATALOGO["pca"]["unidades_de_resultado"] = {
    "item": {"campos_identificadores": ["id_item"]},
    "categoria": {"campos_identificadores": ["categoria"]},
    "unidade_responsavel": {
        "campos_identificadores": ["unidade_responsavel"]
    },
}

PROMPT = '\nConverta o pedido em um plano. Não calcule nem responda à pergunta.\nUse somente o catálogo. Retorne JSON, sem Markdown.\n\nEstrutura:\n{"tipo":"plano","mensagem":"","pedido_documental":null,\n "plano":{"fonte":"nome_da_fonte","tarefas":[],\n "comparacoes":[],"formato":"automatico","pendencias":[]}}\n\nTarefas permitidas:\n- Contar registros: {"id":"x","operacao":"contar",\n  "filtros":[],"agrupar_por":[]}\n- Contar campo preenchido ou valores distintos:\n  operacao contar_preenchidos ou contar_distintos, com id, campo,\n  filtros e agrupar_por.\n- Soma: {"id":"x","operacao":"somar","campo":"campo_numerico",\n  "filtros":[],"agrupar_por":[]}\n- Média aritmética: {"id":"x","operacao":"media","campo":"campo_numerico",\n  "filtros":[],"agrupar_por":[]}\n- Mínimo: {"id":"x","operacao":"minimo","campo":"campo_numerico",\n  "filtros":[],"agrupar_por":[]}\n- Máximo: {"id":"x","operacao":"maximo","campo":"campo_numerico",\n  "filtros":[],"agrupar_por":[]}\n- Listar: id, operacao listar, filtros, campos, distintos,\n  limite de 1 a 100, ordenar_por e ordem crescente ou decrescente.\n  distintos é booleano obrigatório: true ou false; não omita o campo.\n  Para identificar entidades sem repetição, use distintos true e somente\n  os campos da entidade. Para listar registros, preserve seu identificador.\n\n\nUNIDADE DO RESULTADO\nAntes de escolher a operação e as colunas, identifique o que o usuário\nquer obter: registros, entidades, medidas ou resultados por grupo.\nUse as unidades_de_resultado do catálogo como referência.\nOs campos usados nos filtros não precisam aparecer na resposta.\nIdentificar entidades exige somente seus campos identificadores e\ndistintos true. Acrescentar o identificador de cada registro muda a\nunidade do resultado e impede remover repetições da entidade.\nInclua os registros associados somente se essa associação for pedida.\nIdentificar registros exige preservar o identificador do registro.\nExemplo: identificar as unidades responsáveis com itens da categoria\nMaterial exige listar unidade_responsavel com distintos true e filtrar\ncategoria igual Material. Não exige listar id_item.\nUma contagem, soma ou outra medida deve conservar a unidade pedida.\n\nFiltro: {"campo":"nome","operador":"igual","valor":"valor"}.\nOperadores: igual, diferente, contem, em, maior, maior_igual,\nmenor, menor_igual. em usa lista de strings.\nTodos os filtros ficam nas tarefas e são combinados por E.\nUma comparação de grupos usa tarefas separadas.\nComparação: {"id":"c","operacao":"diferenca",\n"esquerda":"id_da_tarefa","direita":"id_da_tarefa"}.\ndiferenca subtrai os resultados; razao divide; percentual divide e multiplica por cem.\nIDs curtos. Número de itens significa contar registros.\nQuantidade física de produto não significa número de itens.\nCrie somente as tarefas pedidas. Comparar não exige listar registros.\nNão coloque campos de listagem em contagens.\nFormato: automatico, texto ou tabela.\nSe faltar informação essencial, use tipo esclarecimento,\nmensagem explicativa e plano null.\n\n\nAGRUPAMENTO NÃO É CONTAGEM DE VALORES DISTINTOS\n- Para uma medida por grupo, categoria ou outro campo, use agrupar_por.\n  O resultado deve apresentar a medida separadamente para cada grupo.\n- Contar registros por um campo: operacao contar, agrupar_por com esse campo.\n- Somar valores por um campo: operacao somar, campo numérico da soma,\n  agrupar_por com o campo que define os grupos.\n- contar_distintos retorna um único número de valores diferentes.\n  Não responde quantos registros existem em cada valor.\n- Uma tabela de quantidades por grupo exige as quantidades de cada grupo,\n  não somente o número de grupos.\n- O formato tabela determina a apresentação, não substitui o agrupamento.\nAntes de retornar, confira se o plano produz as informações solicitadas,\ne não apenas uma operação relacionada às mesmas palavras.\n\n\nA operação deve usar exatamente um dos nomes válidos; medir não é operação.\nMédia aritmética é a soma dos valores disponíveis dividida pela quantidade\nde registros com valor disponível.\nUma média por item ou por registro, sem pedido de separação em grupos,\nusa operacao media com agrupar_por vazio.\nNão agrupe por identificador apenas porque o item é a unidade da média.\nAgrupamento é necessário quando o usuário pede uma medida separada\npara cada categoria, fornecedor ou outro grupo.\nNão substitua média ponderada ou preço por unidade por média aritmética.\n'


PROMPT += """
INSTRUÇÕES DE APRESENTAÇÃO DA RESPOSTA FINAL
Pedidos como responder em uma frase, ser breve ou mostrar uma tabela
se referem à resposta destinada ao usuário.
Nesta etapa, retorne exclusivamente o JSON completo do planejamento.
Não escreva a resposta final e não sacrifique a sintaxe JSON para
seguir uma instrução de brevidade.
O pedido de apresentação não muda os filtros nem o cálculo solicitado.
"""


PROMPT += """
MÉDIAS E RAZÕES
Para média aritmética de um campo, prefira uma única tarefa:
operacao media, campo numérico solicitado, filtros pertinentes
e agrupar_por somente quando o usuário pedir resultados por grupo.
Não use media como operação de comparacao: ela é operação de tarefa.
Uma divisão entre resultados usa comparacao com operacao razao.
Se representar uma média como soma dividida por contagem, o denominador
deve contar os valores preenchidos do mesmo campo, com os mesmos filtros.
Não inclua valores ausentes no denominador da média.
Uma razão pode ter unidade derivada, como reais por registro.
Não apresente uma razão com unidade como se fosse uma porcentagem.
"""



PROMPT += """
ESCOLHA PELA INTENÇÃO
A mesma fonte permite contar, identificar registros, listar, agrupar
ou medir. Interprete o pedido completo, independentemente do verbo usado.
Identificar quais registros atendem ao critério exige listar, não contar.
Escolha campos disponíveis que identifiquem esses registros.
Não substitua a identificação por uma contagem.
Se houver vários pedidos, represente todos em tarefas ou no pedido documental.
Uma explicação de conceito ou regra exige documentos, não cálculo no CSV:
use tipo documental, mensagem explicativa, plano null e
pedido_documental null quando não houver tarefa analítica.
Informação ausente ou critério impossível exige esclarecimento.
Não escolha outro processo nem descarte condições para produzir um plano.
"""



PROMPT += """
LIMITES DE APRESENTAÇÃO DOS REGISTROS
Uma tarefa listar aceita limite inteiro de 1 a 100; o padrão é 20.
Não proponha 1000 nem outro limite fora desse intervalo.
O limite controla a exibição, não altera filtros nem o universo do cálculo.
Não apresente uma amostra ou listagem truncada como se estivesse completa.
Identificar entidades, como fornecedores, exige mostrar seus nomes.
Para identificar entidades sem repetição, use listar com distintos true
e somente os campos que identificam as entidades solicitadas.
distintos remove repetições da combinação dos campos antes do limite.
Para listar itens, preserve seu identificador: itens diferentes não
devem desaparecer porque possuem o mesmo fornecedor.
Agrupe e conte por entidade quando também for pedida sua quantidade.
Contar entidades distintas, sozinho, não identifica quais são.
"""


def _schema_estrito(schema):
    """Explicita campos padrão para o formato estruturado do serviço."""
    if isinstance(schema, list):
        return [_schema_estrito(item) for item in schema]
    if not isinstance(schema, dict):
        return schema

    resultado = {
        chave: _schema_estrito(valor)
        for chave, valor in schema.items()
        if chave != "default"
    }
    if resultado.get("type") == "object" and "properties" in resultado:
        resultado["required"] = list(resultado["properties"])
        resultado["additionalProperties"] = False
    return resultado


def interpretar_analitica(
    pergunta, *, client=None, run_id=None, query_id=None
):
    """Propõe, valida e permite uma única correção de plano inválido."""
    from pydantic import ValidationError
    from src.generate import OLLAMA_URL, GENERATION_MODEL

    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("Pergunta vazia.")

    run_id = run_id or obs.novo_run_id()
    query_id = query_id or f"q_{uuid.uuid4().hex[:8]}"

    from src.query_decomposition import separar_pedidos

    partes = separar_pedidos(pergunta)
    pergunta_analitica = partes["analitica"]
    pedido_documental_extraido = partes["documental"]

    # Limites conhecidos são conferidos antes de qualquer chamada ao modelo.
    from src.analytical_capabilities import verificar_limites_conhecidos

    limite_fonte = verificar_limites_conhecidos(pergunta_analitica)
    if limite_fonte is not None:
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="validacao",
            input_data={
                "tipo": "limites_conhecidos_fonte",
                "pergunta": pergunta,
            },
        ) as observacao_limite:
            observacao_limite["output"] = {
                "execucao_bloqueada": True,
                "fonte": limite_fonte["fonte"],
                "alertas": limite_fonte["alertas"],
                "decisao": "esclarecimento",
            }

        return {
            "tipo": "esclarecimento",
            "mensagem": limite_fonte["mensagem"],
            "plano": None,
            "pedido_documental": None,
            "run_id": run_id,
            "query_id": query_id,
            "tentativas": 0,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
        }

    if client is None:
        import httpx
        client = OpenAI(
            base_url=OLLAMA_URL,
            api_key="ollama",
            timeout=httpx.Timeout(
                connect=10.0, read=120.0, write=30.0, pool=10.0
            ),
            max_retries=0,
        )

    from src.analytical_transport import decodificar_interpretacao

    mensagens = [
        {"role": "system", "content": PROMPT},
        {
            "role": "user",
            "content": (
                "CATÁLOGO:\n"
                + json.dumps(CATALOGO, ensure_ascii=False)
                + "\n\nPERGUNTA ANALÍTICA:\n" + pergunta_analitica.strip()
            ),
        },
    ]
    tokens_total = {"prompt": 0, "completion": 0, "total": 0}

    for tentativa in (1, 2):
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="roteamento",
            input_data={
                "pergunta": pergunta,
                "tipo": "planejamento_analitico",
                "pergunta_analitica": pergunta_analitica,
                "pedido_documental_extraido": pedido_documental_extraido,
                "tentativa": tentativa,
            },
            modelo=GENERATION_MODEL,
        ) as observacao:
            resposta = client.chat.completions.create(
                model=GENERATION_MODEL,
                temperature=0,
                max_tokens=4096,
                extra_body={
                    "reasoning_effort": os.getenv(
                        "LLM_REASONING_EFFORT", "none"
                    )
                },
                messages=[dict(mensagem) for mensagem in mensagens],
            )

            escolha = resposta.choices[0]
            uso = getattr(resposta, "usage", None)
            tokens = {
                "prompt": getattr(uso, "prompt_tokens", 0) if uso else 0,
                "completion": getattr(uso, "completion_tokens", 0) if uso else 0,
                "total": getattr(uso, "total_tokens", 0) if uso else 0,
            }
            for chave in tokens_total:
                tokens_total[chave] += tokens[chave] or 0
            observacao["tokens"] = tokens

            conteudo = escolha.message.content
            try:
                proposta = json.loads(conteudo)
            except (ValueError, TypeError):
                proposta = conteudo

            observacao["output"] = {
                "interpretacao_proposta": proposta,
                "validacao": "pendente",
                "tentativa": tentativa,
            }

        try:
            with obs.observar_etapa(
                run_id=run_id,
                query_id=query_id,
                stage="validacao",
                input_data={
                    "tipo": "contrato_plano_analitico",
                    "tentativa": tentativa,
                },
            ) as observacao_validacao:
                if escolha.finish_reason != "stop":
                    raise ValueError(
                        "Planejamento incompleto; não executar. "
                        "Retorne novamente o JSON completo."
                    )
                if not isinstance(conteudo, str) or not conteudo.strip():
                    raise ValueError(
                        "Planejamento vazio; retorne um JSON completo."
                    )
                dados_interpretacao = decodificar_interpretacao(conteudo)
                if pedido_documental_extraido:
                    dados_interpretacao["pedido_documental"] = (
                        pedido_documental_extraido
                    )
                interpretacao = InterpretacaoAnalitica.model_validate(
                    dados_interpretacao
                )
                observacao_validacao["output"] = {
                    "estrutura_e_consistencia_validas": True,
                    "tipo_decisao": interpretacao.tipo,
                    "tentativa": tentativa,
                }

            return {
                **interpretacao.model_dump(),
                "run_id": run_id,
                "query_id": query_id,
                "pergunta_analitica": pergunta_analitica,
                "tentativas": tentativa,
                "tokens": tokens_total,
            }

        except (ValidationError, ValueError) as erro:
            if tentativa == 2:
                raise

            if isinstance(erro, ValidationError):
                erros_resumidos = [
                    {
                        "campo": ".".join(
                            str(parte) for parte in item["loc"]
                        ),
                        "erro": item["msg"],
                    }
                    for item in erro.errors()
                ]
            else:
                erros_resumidos = [{
                    "campo": "saida_do_planejador",
                    "erro": str(erro),
                }]
            mensagens.extend([
                {"role": "assistant", "content": conteudo or ""},
                {
                    "role": "user",
                    "content": (
                        "O plano anterior foi rejeitado e não foi executado.\n"
                        "ERROS DE VALIDAÇÃO:\n" + json.dumps(erros_resumidos, ensure_ascii=False) + "\n\n"
                        "Reinterprete a pergunta original e devolva um plano "
                        "completo corrigido. Preserve todos os pedidos e "
                        "critérios do usuário. Não suprima um requisito para "
                        "passar na validação. Filtros de uma tarefa são "
                        "condições simultâneas: critérios de grupos diferentes "
                        "devem ficar em tarefas separadas. Número de itens "
                        "significa contagem de registros. Se o pedido não "
                        "puder ser atendido, use esclarecimento."
                    ),
                },
            ])
