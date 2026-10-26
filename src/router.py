import json
import os
import re
import time
import uuid
from typing import Any, Dict, List
from openai import OpenAI
try:
    from . import obs  # funciona como src.router ou repositorio1.src.router
except ImportError:  # permite "python src/router.py" direto, sem pacote.
    import obs
OLLAMA_URL = "http://ecoa-llm.duckdns.org:11434/v1"
GENERATION_MODEL = "qcwind/qwen3-8b-instruct-Q4-K-M"
ROTAS_VALIDAS = {
    "normativa",
    "estruturada",
    "conversacional",
    "agregada",
}
# Campos de filtro que só devem ser aceitos se aparecerem
# explicitamente no texto da pergunta (evita filtro inventado pelo LLM).
CAMPOS_FILTRO_VALIDADOS_NO_TEXTO = [
    "ano",
    "modalidade",
    "municipio",
    "fornecedor",
]
PROMPT_ROTEADOR = """

Você é o roteador de um sistema Adaptive RAG sobre contratações públicas

do Estado do Rio de Janeiro.



Sua tarefa não é decidir apenas pelo assunto da pergunta. Você deve decidir

qual tipo de evidência é necessário para respondê-la.



As bases disponíveis são:



1. normativa:

   Leis, decretos, editais, regras, requisitos, permissões, proibições,

   modalidades e vigência de normas.



2. estruturada:

   Contratos, fornecedores, órgãos, municípios, CNPJ, valores, datas,

   situação da contratação e objeto contratado.



3. conversacional:

   Atas, e-mails, manifestações, reclamações, dúvidas e comunicações.



4. agregada:

   Médias, totais, somas, séries históricas, comparações estatísticas

   e valores agrupados.



Uma pergunta pode exigir mais de uma base.



Exemplos:



Pergunta:

"Sou MEI, posso participar de pregão eletrônico? Existe algum aberto?"

Rotas:

["normativa", "estruturada"]



Pergunta:

"Qual foi o valor médio do arroz contratado em 2025?"

Rotas:

["agregada", "estruturada"]



Pergunta:

"Quantos contratos foram assinados por modalidade em 2025?"

Rotas:

["agregada", "estruturada"]



Pergunta:

"Quais contratos de software ficaram acima de R$ 500 mil?"

Rotas:

["estruturada"]



Pergunta:

"O que foi discutido nas atas sobre a compra de equipamentos?"

Rotas:

["conversacional"]



Importante:

- Perguntas que pedem quantidade, média, total, soma, percentual ou agrupamento

  exigem a base agregada.

- Perguntas sobre o Plano de Contratações Anual ou PCA devem usar

  a base agregada. Inclua também a estruturada somente se a pergunta

  exigir comparação com contratos efetivamente realizados.

- Quando a pergunta pedir especificamente o conteúdo de atas, e-mails,

  reclamações ou manifestações, use a base conversacional.

- Não adicione uma base somente porque a pergunta menciona compra,

  contrato ou modalidade. Identifique qual tipo de evidência foi solicitado.



Regras de extração de filtros:

- Extraia um filtro SOMENTE se o valor estiver explícito na pergunta.

- "serviços de tecnologia" é o OBJETO da contratação, não uma modalidade.

  Modalidade só deve ser preenchida se a pergunta citar termos como

  "pregão eletrônico", "concorrência", "dispensa", "inexigibilidade" etc.

- Nunca preencha "ano" se a pergunta não mencionar um ano explicitamente.

- Se não houver evidência textual de um filtro, retorne null para esse campo.



Regras de segurança:



- Não faça acusações de fraude ou ilegalidade.

- Não exponha CPF, dados bancários, credenciais, telefone pessoal ou e-mail pessoal.

- Perguntas que pedem acusação ou conclusão jurídica devem ser marcadas

  para recusa parcial ou total.

- O sistema pode apresentar dados públicos e explicar normas.

- Não responda à pergunta. Apenas analise e classifique.



Retorne exclusivamente JSON válido no formato:



{

  "routes": ["estruturada"],

  "filters": {

    "uf": "RJ",

    "ano": 2025,

    "valor_minimo": null,

    "valor_maximo": null,

    "modalidade": null,

    "municipio": null,

    "fornecedor": null

  },

  "is_refusal": false,

  "refusal_reason": null,

  "justification": "Explicação curta da escolha das rotas."

}


Regra sobre comunicações e processos fictícios:
- Comunicações sintéticas e processos explicitamente fictícios são fontes
  da base conversacional. Pedidos sobre prazos por item, entregas parciais
  ou condições informadas nessas comunicações exigem essa base, mesmo
  quando a pergunta não repete a palavra "comunicação".
- A menção a processo, item ou entrega não justifica, sozinha, selecionar
  a base estruturada. Escolha a natureza da evidência solicitada.
- Não acrescente outras bases sem um pedido que necessite delas.
- Identificadores são valores completos: uma sigla dentro de um código
  de processo não representa, sozinha, um filtro geográfico.

"""


def _extrair_json(texto: str) -> Dict[str, Any]:
    """

    Extrai um objeto JSON mesmo quando o modelo inclui marcação Markdown.

    """
    texto = texto.strip()
    texto = texto.replace("```json", "").replace("```", "").strip()
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise ValueError("O modelo não retornou um objeto JSON.")
    return json.loads(texto[inicio : fim + 1])


def _normalizar_rotas(rotas: Any) -> List[str]:
    """

    Mantém somente as quatro rotas permitidas, sem repetição.

    """
    if not isinstance(rotas, list):
        return []
    resultado = []
    for rota in rotas:
        rota_normalizada = str(rota).strip().lower()
        if rota_normalizada in ROTAS_VALIDAS:
            if rota_normalizada not in resultado:
                resultado.append(rota_normalizada)
    return resultado


def _normalizar_texto_para_comparacao(texto: str) -> str:
    """

    Remove pontuação e espaços repetidos antes de comparar.

    O LLM costuma normalizar valores (ex.: "Pregão - Eletrônico"),

    enquanto a pergunta original vem sem essa formatação

    (ex.: "pregão eletrônico"). Sem essa normalização, a comparação

    literal descarta filtros válidos por engano.

    """
    texto = texto.lower()
    texto = re.sub(r"[^\wà-ÿ\s]", " ", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _converter_valor_monetario(
    numero_texto: str,
    unidade: str | None,
) -> float:
    """

    Converte valores monetários escritos em formato brasileiro.

    Exemplos:

    500 mil -> 500000

    1 milhão -> 1000000

    1,5 milhão -> 1500000

    750.000 -> 750000

    """
    numero_texto = numero_texto.strip()
    if "," in numero_texto:
        numero_normalizado = (
            numero_texto
            .replace(".", "")
            .replace(",", ".")
        )
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", numero_texto):
        numero_normalizado = numero_texto.replace(".", "")
    else:
        numero_normalizado = numero_texto
    valor = float(numero_normalizado)
    unidade = (unidade or "").lower().strip()
    if unidade == "mil":
        valor *= 1_000
    elif unidade in {
        "milhão",
        "milhao",
        "milhões",
        "milhoes",
    }:
        valor *= 1_000_000
    return valor


def _extrair_filtros_monetarios(
    pergunta: str,
) -> Dict[str, float | None]:
    """

    Extrai limites monetários diretamente da pergunta.

    A extração determinística impede que o LLM transforme,

    por exemplo, R$ 500 mil em R$ 500 milhões.

    """
    texto = pergunta.lower()
    numero = r"([\d]+(?:[.,][\d]+)*)"
    unidade = (
        r"(milhões|milhoes|milhão|milhao|mil)?"
    )
    padrao_minimo = re.search(
        rf"(?:acima\s+de|superior(?:es)?\s+a|mais\s+de)"
        rf"\s+(?:r\$\s*)?{numero}\s*{unidade}",
        texto,
    )
    padrao_maximo = re.search(
        rf"(?:abaixo\s+de|inferior(?:es)?\s+a|menos\s+de|"
        rf"até|ate)\s+(?:r\$\s*)?{numero}\s*{unidade}",
        texto,
    )
    valor_minimo = None
    valor_maximo = None
    if padrao_minimo:
        valor_minimo = _converter_valor_monetario(
            padrao_minimo.group(1),
            padrao_minimo.group(2),
        )
    if padrao_maximo:
        valor_maximo = _converter_valor_monetario(
            padrao_maximo.group(1),
            padrao_maximo.group(2),
        )
    return {
        "valor_minimo": valor_minimo,
        "valor_maximo": valor_maximo,
    }


def _remover_referencias_pregao(texto: str) -> str:
    """Separa identificadores de pregão dos critérios geográficos e temporais."""
    return re.sub(
        r"\bpe\s*(?:(?:numero|n[.º°o]*)\s*)?"
        r"\d+(?:\s*/\s*\d+){1,2}\b",
        " ",
        texto,
        flags=re.IGNORECASE,
    )


def _extrair_ufs_explicitas(pergunta: str) -> set[str]:
    """Reconhece siglas de UF em contexto de localização, fora de IDs."""
    from src.document_scope import PADRAO_PROCESSO_ALFANUMERICO, normalizar

    texto = PADRAO_PROCESSO_ALFANUMERICO.sub(
        " ", normalizar(_remover_referencias_pregao(pergunta))
    )
    texto = _normalizar_texto_para_comparacao(texto)
    validas = set(
        "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI "
        "RJ RN RS RO RR SC SP SE TO".split()
    )
    candidatas = re.findall(
        r"\b(?:no|na|em|do|da)\s+([a-z]{2})\b"
        r"|\buf\s*[:=]?\s*([a-z]{2})\b",
        texto,
    )
    encontradas = {
        (primeira or segunda).upper()
        for primeira, segunda in candidatas
        if (primeira or segunda).upper() in validas
    }

    # Preserva as formas de RJ já suportadas, após remover identificadores.
    if re.search(r"\brj\b", texto) or "rio de janeiro" in texto:
        encontradas.add("RJ")
    return encontradas


def _extrair_uf_explicita(pergunta: str) -> str | None:
    ufs = _extrair_ufs_explicitas(pergunta)
    return next(iter(ufs)) if len(ufs) == 1 else None


def _validar_filtros_contra_pergunta(
    pergunta: str,
    filtros: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """

    Remove filtros inventados pelo modelo e corrige valores

    monetários utilizando diretamente o texto da pergunta.

    """
    if not isinstance(filtros, dict):
        filtros = {}
    filtros = dict(filtros)
    texto = _normalizar_texto_para_comparacao(
        _remover_referencias_pregao(pergunta)
    )
    for campo in CAMPOS_FILTRO_VALIDADOS_NO_TEXTO:
        valor = filtros.get(campo)
        if (
            valor
            and _normalizar_texto_para_comparacao(
                str(valor)
            ) not in texto
        ):
            filtros[campo] = None
    limites = _extrair_filtros_monetarios(pergunta)
    # Se a pergunta não contém limite explícito, qualquer
    # valor sugerido pelo modelo é descartado.
    filtros["valor_minimo"] = limites["valor_minimo"]
    filtros["valor_maximo"] = limites["valor_maximo"]
    # A UF só pode ser aplicada quando estiver explícita na pergunta.
    filtros["uf"] = _extrair_uf_explicita(pergunta)
    if (
        filtros["uf"]
        and str(filtros.get("municipio") or "").strip().upper()
        == filtros["uf"]
    ):
        filtros["municipio"] = None
    ano = filtros.get("ano")
    if ano is not None and not re.search(
        r"\b" + re.escape(str(ano)) + r"\b", texto
    ):
        filtros["ano"] = None
    filtros.setdefault("ano", None)
    filtros.setdefault("modalidade", None)
    filtros.setdefault("municipio", None)
    filtros.setdefault("fornecedor", None)
    return filtros


def _roteamento_fallback(pergunta: str) -> Dict[str, Any]:
    """

    Roteamento emergencial utilizado somente quando o modelo não responde.

    O roteamento principal deve ser feito pelo LLM, pois a classificação

    somente por palavras-chave não é suficiente para o Adaptive RAG.

    """
    texto = pergunta.lower()
    rotas = []
    termos_recusa = [
        "foi uma fraude",
        "é uma fraude",
        "e uma fraude",
        "contrato fraudulento",
        "foi ilegal",
        "é ilegal",
        "e ilegal",
        "houve corrupção",
        "houve corrupcao",
    ]
    if any(termo in texto for termo in termos_recusa):
        return {
            "routes": [],
            "filters": {
                "uf": None,
                "ano": None,
                "valor_minimo": None,
                "valor_maximo": None,
                "modalidade": None,
                "municipio": None,
                "fornecedor": None,
            },
            "is_refusal": True,
            "refusal_reason": (
                "Pergunta envolve acusação de fraude ou "
                "ilegalidade, que não pode ser determinada "
                "pelo sistema."
            ),
            "justification": (
                "Recusa aplicada pelas regras de segurança."
            ),
        }
    termos_agregados = [
        "média",
        "media",
        "total",
        "quantos",
        "quantas",
        "soma",
        "comparação",
        "comparar",
        "percentual",
        "plano de contratações anual",
        "plano de contratacoes anual",
        "pca",
    ]
    termos_normativos = [
        "lei",
        "decreto",
        "norma",
        "pode participar",
        "posso participar",
        "permitido",
        "proibido",
        "obrigatório",
        "obrigatorio",
        "regra",
        "requisito",
        "requisitos",
        "mei",
        "vigente",
    ]
    termos_conversacionais = [
        "reclamação",
        "reclamacao",
        "e-mail",
        "email",
        "manifestação",
        "manifestacao",
        "ouvidoria",
    ]
    termos_estruturados = [
        "contrato",
        "contratos",
        "contratação",
        "contratacao",
        "contratações",
        "contratacoes",
        "fornecedor",
        "cnpj",
        "empresa",
        "órgão",
        "orgao",
        "município",
        "municipio",
        "valor",
        "licitação",
        "licitacao",
    ]
    if any(termo in texto for termo in termos_agregados):
        rotas.append("agregada")
    if any(termo in texto for termo in termos_normativos):
        rotas.append("normativa")
    consulta_conversacional = (
        any(
            termo in texto
            for termo in termos_conversacionais
        )
        or re.search(r"\batas?\b", texto) is not None
    )
    if consulta_conversacional:
        rotas.append("conversacional")
    if any(termo in texto for termo in termos_estruturados):
        rotas.append("estruturada")
    if not rotas:
        rotas = ["estruturada"]
    ano_encontrado = re.search(r"\b(20\d{2})\b", texto)
    valor_minimo = None
    valor_encontrado = re.search(
        r"(?:acima\s+de|superior(?:es)?\s+a|mais\s+de)\s+"
        r"(?:r\$\s*)?([\d.,]+)\s*(milhões|milhoes|milhão|mil)?",
        texto,
    )
    if valor_encontrado:
        numero = valor_encontrado.group(1).replace(".", "").replace(",", ".")
        valor_minimo = float(numero)
        unidade = valor_encontrado.group(2)
        if unidade == "mil":
            valor_minimo *= 1_000
        elif unidade in {"milhão", "milhoes", "milhões"}:
            valor_minimo *= 1_000_000
    return {
        "routes": rotas,
        "filters": {
            "uf": _extrair_uf_explicita(pergunta),
            "ano": int(ano_encontrado.group(1)) if ano_encontrado else None,
            "valor_minimo": valor_minimo,
            "valor_maximo": None,
            "modalidade": None,
            "municipio": None,
            "fornecedor": None,
        },
        "is_refusal": False,
        "refusal_reason": None,
        "justification": "Roteamento de contingência aplicado porque o modelo não respondeu.",
    }


def analisar_consulta(
    pergunta: str,
    client: OpenAI | None = None,
    run_id: str | None = None,
) -> Dict[str, Any]:
    """

    Analisa a pergunta e retorna rotas, filtros e decisão de segurança.

    run_id agrupa, no log JSONL do obs.py, as etapas "query_analysis" e

    "roteamento" desta mesma chamada. É opcional: quando quem chama (por

    exemplo o retrieve.py ou os testes) não informa um run_id, um novo é

    gerado aqui mesmo, então nada quebra em quem já usava a função sem

    esse parâmetro.

    """
    inicio = time.perf_counter()
    query_id = f"q_{uuid.uuid4().hex[:8]}"
    if not pergunta or not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")
    run_id = run_id or obs.novo_run_id()
    pergunta_limpa = pergunta.strip()
    # Etapa "query_analysis": registra a pergunta recebida antes de decidir
    # rotas. Não envolve chamada ao LLM, então dificilmente falha; mesmo
    # assim fica dentro do observar_etapa para logar erro caso ocorra.
    with obs.observar_etapa(
        run_id=run_id,
        query_id=query_id,
        stage="query_analysis",
        input_data={"pergunta": pergunta_limpa},
    ) as observacao_analise:
        observacao_analise["output"] = {
            "tamanho_pergunta": len(pergunta_limpa),
        }
    # Guardrail P06: impedir exposicao de dados pessoais.
    texto_privacidade = _normalizar_texto_para_comparacao(
        pergunta_limpa
    )

    import unicodedata

    texto_privacidade = "".join(
        c for c in unicodedata.normalize(
            "NFKD", texto_privacidade
        )
        if not unicodedata.combining(c)
    )

    pede_exposicao = bool(
        re.search(
            r"\b(?:mostre|liste|informe|exiba|revele|forneca)\b",
            texto_privacidade
        )
    )
    menciona_dado_pessoal = bool(
        re.search(
            r"\bcpf\b|telefone pessoal|e-mail pessoal|email pessoal",
            texto_privacidade
        )
    )
    pede_protecao = bool(
        re.search(
            r"\b(?:oculte|mascare|anonimize|proteja)\b",
            texto_privacidade
        )
    )

    if pede_exposicao and menciona_dado_pessoal and not pede_protecao:
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="roteamento",
            input_data={"pergunta": pergunta_limpa},
            modelo=GENERATION_MODEL,
        ) as observacao_recusa:
            observacao_recusa["output"] = {
                "routes": [],
                "filters": {},
                "is_refusal": True,
                "tipo_recusa": "privacidade",
            }
            observacao_recusa["tokens"] = {
                "prompt": 0,
                "completion": 0,
                "total": 0,
            }

        return {
            "routes": [],
            "filters": {
                "uf": None,
                "ano": None,
                "valor_minimo": None,
                "valor_maximo": None,
                "modalidade": None,
                "municipio": None,
                "fornecedor": None,
            },
            "is_refusal": True,
            "refusal_reason": (
                "Nao posso expor CPF, telefone pessoal "
                "ou e-mail pessoal."
            ),
            "justification": (
                "Recusa por protecao de dados pessoais."
            ),
            "router_fallback": False,
            "query": pergunta_limpa,
            "query_id": query_id,
            "stage": "roteamento",
            "latencia_ms": round(
                (time.perf_counter() - inicio) * 1000, 2
            ),
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0,
            },
            "modelo": GENERATION_MODEL,
        }

    # Guardrail P09: previsao de valores sem modelo validado.
    import unicodedata

    texto_previsao = _normalizar_texto_para_comparacao(pergunta_limpa)
    texto_previsao = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto_previsao)
        if not unicodedata.combining(caractere)
    )
    pede_previsao = bool(
        re.search(
            r"\b(?:sera|previsao|prever|preveja)\b",
            texto_previsao
        )
        and re.search(
            r"valor medio|media das contratacoes",
            texto_previsao
        )
    )
    if pede_previsao:
        resultado = {
            "routes": [],
            "filters": {
                "uf": None,
                "ano": None,
                "valor_minimo": None,
                "valor_maximo": None,
                "modalidade": None,
                "municipio": None,
                "fornecedor": None,
            },
            "is_refusal": True,
            "refusal_reason": (
                "O sistema nao possui modelo validado para "
                "prever valores futuros de contratacoes."
            ),
            "justification": (
                "Recusa por limite de escopo e ausencia "
                "de evidencia preditiva validada."
            ),
            "router_fallback": False,
            "query": pergunta_limpa,
            "query_id": query_id,
            "stage": "roteamento",
            "latencia_ms": round(
                (time.perf_counter() - inicio) * 1000, 2
            ),
            "tokens": {
                "prompt": 0,
                "completion": 0,
                "total": 0,
            },
            "modelo": GENERATION_MODEL,
        }
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="roteamento",
            input_data={"pergunta": pergunta_limpa},
            modelo=GENERATION_MODEL,
        ) as observacao_recusa:
            observacao_recusa["output"] = {
                "routes": [],
                "filters": {},
                "is_refusal": True,
                "tipo_recusa": "limite_de_escopo",
            }
            observacao_recusa["tokens"] = {
                "prompt": 0,
                "completion": 0,
                "total": 0,
            }

        return resultado

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
    try:
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="roteamento",
            input_data={"pergunta": pergunta_limpa},
            modelo=GENERATION_MODEL,
        ) as observacao_roteamento:
            resposta = client.chat.completions.create(
                model=GENERATION_MODEL,
                temperature=0,
                max_tokens=int(os.getenv("ROUTER_MAX_TOKENS", "512")),
                extra_body={
                    "reasoning_effort": os.getenv(
                        "LLM_REASONING_EFFORT", "none"
                    ),
                },
                messages=[
                    {
                        "role": "system",
                        "content": PROMPT_ROTEADOR,
                    },
                    {
                        "role": "user",
                        "content": pergunta_limpa,
                    },
                ],
            )
            conteudo = resposta.choices[0].message.content
            resultado = _extrair_json(conteudo)
            resultado["routes"] = _normalizar_rotas(
                resultado.get("routes", [])
            )
            # Importante: setdefault ANTES de validar, senão resultado["filters"]
            # pode não existir (KeyError) ou vir como null (AttributeError).
            resultado.setdefault("filters", {})
            resultado["filters"] = _validar_filtros_contra_pergunta(
                pergunta,
                resultado["filters"],
            )
            resultado.setdefault("is_refusal", False)
            resultado.setdefault("refusal_reason", None)
            resultado.setdefault("justification", "")
            texto_consulta = (
                _normalizar_texto_para_comparacao(
                    pergunta_limpa
                )
            )
            consulta_pca = (
                "plano de contratações anual"
                in texto_consulta
                or "plano de contratacoes anual"
                in texto_consulta
                or re.search(
                    r"\bpca\b",
                    texto_consulta,
                )
            )
            if consulta_pca:
                termos_cross_source = [
                    "contratos assinados",
                    "contratacoes realizadas",
                    "contratações realizadas",
                    "fornecedores contratados",
                    "comparar com contratos",
                ]
                if any(
                    termo in texto_consulta
                    for termo in termos_cross_source
                ):
                    resultado["routes"] = [
                        "agregada",
                        "estruturada",
                    ]
                else:
                    resultado["routes"] = ["agregada"]
            if resultado["is_refusal"]:
                resultado["routes"] = []
                resultado["filters"] = {
                    "uf": None,
                    "ano": None,
                    "valor_minimo": None,
                    "valor_maximo": None,
                    "modalidade": None,
                    "municipio": None,
                    "fornecedor": None,
                }
            elif not resultado["routes"]:
                resultado["routes"] = ["estruturada"]
            uso = getattr(resposta, "usage", None)
            tokens = {
                "prompt": getattr(uso, "prompt_tokens", 0) if uso else 0,
                "completion": getattr(uso, "completion_tokens", 0) if uso else 0,
                "total": getattr(uso, "total_tokens", 0) if uso else 0,
            }
            resultado["router_fallback"] = False
            observacao_roteamento["output"] = {
                "routes": resultado["routes"],
                "filters": resultado["filters"],
                "is_refusal": resultado["is_refusal"],
            }
            observacao_roteamento["tokens"] = tokens
    except Exception as erro:
        resultado = _roteamento_fallback(pergunta)
        resultado["router_fallback"] = True
        resultado["router_error"] = str(erro)
        tokens = {
            "prompt": 0,
            "completion": 0,
            "total": 0,
        }
    resultado["query"] = pergunta_limpa
    resultado["query_id"] = query_id
    resultado["stage"] = "roteamento"
    resultado["latencia_ms"] = round(
        (time.perf_counter() - inicio) * 1000,
        2,
    )
    resultado["tokens"] = tokens
    resultado["modelo"] = GENERATION_MODEL
    return resultado


def _extrair_mes_publicacao(texto):
    """Reconhece um único mês explícito de publicação."""
    import calendar
    if not re.search(r"\bpublicad[oa]s?\b|\bpublicacao\b", texto):
        return None
    # Intervalos e comparações mais complexos exigem esclarecimento.
    if re.search(
        r"\b(?:entre|antes|depois|desde|ate)\b",
        texto,
    ):
        return None
    meses = {
        "janeiro": 1, "fevereiro": 2, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6,
        "julho": 7, "agosto": 8, "setembro": 9,
        "outubro": 10, "novembro": 11, "dezembro": 12,
    }
    mencoes = re.findall(
        r"\b(" + "|".join(meses) + r")\b",
        texto,
    )
    if len(mencoes) != 1:
        return None
    correspondencia = re.search(
        r"\bem\s+(" + "|".join(meses) + r")\s+de\s+(20\d{2})\b",
        texto,
    )
    if not correspondencia:
        return None
    mes = meses[correspondencia.group(1)]
    ano = int(correspondencia.group(2))
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return {
        "data_inicial": f"{ano:04d}-{mes:02d}-01",
        "data_final": f"{ano:04d}-{mes:02d}-{ultimo_dia:02d}",
    }


def _extrair_paginacao_explicita(texto):
    """Extrai paginação explícita de texto previamente normalizado."""
    ordinais = {
        "primeira": 1,
        "segunda": 2,
        "terceira": 3,
        "quarta": 4,
        "quinta": 5,
    }
    if re.search(r"\b(?:proxima|anterior|ultima)\s+pagina\b", texto):
        raise ValueError(
            "Informe o número da página. Navegação relativa "
            "ainda não está implementada."
        )
    if re.search(r"\bpagina\s+\d+\s*(?:e|a|ate|-)\s*\d+", texto):
        raise ValueError("Solicite uma página por vez.")
    tamanhos = re.findall(
        r"\b(-?\d+)\s+(?:registros?|resultados?|itens?)\s+por\s+pagina\b",
        texto,
    )
    # Remove a indicação de tamanho antes de procurar a página solicitada.
    texto_paginas = re.sub(
        r"\b-?\d+\s+(?:registros?|resultados?|itens?)\s+por\s+pagina\b",
        "",
        texto,
    )
    paginas_numericas = re.findall(
        r"\bpagina\s+(-?\d+)\b",
        texto_paginas,
    )
    paginas_ordinais = [
        ordinais[palavra]
        for palavra in re.findall(
            r"\b(" + "|".join(ordinais) + r")\s+pagina\b",
            texto_paginas,
        )
    ]
    paginas = [int(p) for p in paginas_numericas] + paginas_ordinais
    if len(paginas) > 1 or len(tamanhos) > 1:
        raise ValueError("Informe apenas uma página e um tamanho.")
    restante = re.sub(r"\bpagina\s+-?\d+\b", "", texto_paginas)
    restante = re.sub(
        r"\b(" + "|".join(ordinais) + r")\s+pagina\b",
        "",
        restante,
    )
    if re.search(r"\bpagina\b", restante):
        raise ValueError(
            "Não consegui interpretar a paginação. "
            "Use 'página 2' e '10 registros por página'."
        )
    pagina = paginas[0] if paginas else 1
    tamanho = int(tamanhos[0]) if tamanhos else 20
    if pagina < 1:
        raise ValueError("A página deve ser maior ou igual a 1.")
    if not 1 <= tamanho <= 100:
        raise ValueError("Solicite entre 1 e 100 registros por página.")
    return {"pagina": pagina, "tamanho_pagina": tamanho}
ROTAS_DOCUMENTAIS = {"normativa", "conversacional"}
CAMPOS_SAIDA_ALIASES = {
    "id_pncp": ("id", "identificador"),
    "objeto": ("objeto",),
    "municipio": ("municipio",),
    "uf": ("uf",),
    "ano_compra": ("ano",),
    "valor_estimado": ("valor estimado",),
    "valor_homologado": ("valor homologado",),
    "fornecedor": ("fornecedor",),
}


def _identificar_intencao_estruturada(texto: str) -> tuple[bool, bool, bool]:
    """Identifica menção a contratações e intenção de contar ou listar."""
    menciona_contratacao = bool(
        re.search(r"\b(?:contratos?|contratacoes|contratacao)\b", texto)
    )
    contar = bool(
        re.search(r"\b(?:quantos|quantas)\b", texto)
        or re.search(r"\b(?:total|numero|quantidade)\s+de\b", texto)
    )
    listar = bool(
        re.search(r"\b(?:liste|listar|listagem|relacione)\b", texto)
        or re.search(
            r"\bquais\s+(?:os\s+|as\s+)?(?:contratos?|contratacoes)\b",
            texto,
        )
    )
    return menciona_contratacao, contar, listar


def _rotas_de_recuperacao(rotas: List[str]) -> List[str]:
    """Mantém somente rotas documentais usadas pela recuperação híbrida."""
    return [rota for rota in rotas if rota in ROTAS_DOCUMENTAIS]


def _eh_consulta_pca(texto: str) -> bool:
    """Indica se a pergunta trata explicitamente do PCA."""
    return bool(
        re.search(r"\bpca\b", texto)
        or "plano de contratacoes anual" in texto
    )


def _bases_da_consulta_combinada(
    rotas: List[str],
    rotas_recuperacao: List[str],
) -> List[str]:
    """
    Monta as bases efetivamente executáveis na estratégia combinada.

    A rota agregada não entra aqui porque contagem/listagem simples é
    resolvida deterministicamente pela base estruturada.
    """
    bases = list(rotas_recuperacao)
    if "estruturada" in rotas and "estruturada" not in bases:
        bases.append("estruturada")
    return bases


def _extrair_campos_saida(texto: str) -> List[str] | None:
    """Extrai campos pedidos em frases como 'mostre apenas objeto e valor'."""
    selecao = re.search(
        r"\b(?:apenas|somente)\s+(.+?)(?:[.;?]|$)",
        texto,
    )
    if not selecao:
        return None
    trecho = selecao.group(1)
    return [
        campo
        for campo, nomes in CAMPOS_SAIDA_ALIASES.items()
        if any(
            re.search(r"\b" + re.escape(nome) + r"\b", trecho)
            for nome in nomes
        )
    ]



def _solicita_calculo_media(texto):
    """Distingue pedido de cálculo monetário de pergunta explicativa."""
    menciona_media = bool(re.search(
        r"\b(?:valor|preco|custo)\s+medi[oa]\b"
        r"|\bmedia\s+(?:aritmetica|ponderada)\b"
        r"|\bmedia\s+d[ao]s?\s+(?:valores|precos|custos|contratacoes|compras)\b",
        texto,
    ))
    if not menciona_media:
        return False

    explicativa = bool(
        re.match(r"^(?:explique|como|o que)\b", texto)
        or re.match(
            r"^qual\b.{0,40}\b(?:definicao|conceito|formula|metodo)\b",
            texto,
        )
    )
    if explicativa:
        return False

    return bool(
        re.match(
            r"^(?:por favor[, ]+)?"
            r"(?:qual|quais|quanto|informe|apresente|mostre)\b",
            texto,
        )
        or re.search(r"\b(?:calcule|calcular|obtenha|determine)\b", texto)
    )


def planejar_consulta(
    pergunta,
    client=None,
    run_id=None,
    criterio_tecnologia=None,
    analise=None,
):
    """
    Planeja a estratégia de consulta sem alterar as APIs já usadas pelo sistema.

    Consultas de contagem/listagem usam a base estruturada. Quando a mesma
    pergunta também exige evidência normativa ou conversacional, o plano é
    marcado como ``combinada`` e preserva as rotas documentais para o executor.
    """
    try:
        from .structured_query import normalizar_texto
    except ImportError:
        from src.structured_query import normalizar_texto
    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")
    if analise is None:
        analise = analisar_consulta(
            pergunta,
            client=client,
            run_id=run_id,
        )
    texto_completo = normalizar_texto(pergunta)
    texto = _separar_campos_de_exibicao(texto_completo)
    periodo_publicacao = _extrair_mes_publicacao(texto)
    rotas = list(analise.get("routes", []))
    plano = {
        "bases": rotas,
        "estrategia": "recuperacao_hibrida",
        "operacao": "buscar",
        "filtros": {},
        "campos": None,
        "pagina": 1,
        "tamanho_pagina": 20,
        "query_id": analise.get("query_id"),
        "is_refusal": bool(analise.get("is_refusal")),
        "refusal_reason": analise.get("refusal_reason"),
        "necessita_esclarecimento": False,
        "pergunta_esclarecimento": None,
    }
    # Proteções determinísticas dos casos das personas.
    pede_exposicao = bool(
        re.search(
            r"\b(?:mostre|liste|informe|exiba|revele|forneca)\b",
            texto,
        )
    )
    menciona_dado_pessoal = bool(
        re.search(
            r"\bcpf\b|telefone pessoal|e-mail pessoal|email pessoal",
            texto,
        )
    )
    pede_protecao = bool(
        re.search(
            r"\b(?:oculte|mascare|anonimize|proteja)\b",
            texto,
        )
    )
    if pede_exposicao and menciona_dado_pessoal and not pede_protecao:
        plano["is_refusal"] = True
        plano["tipo_recusa"] = "privacidade"
        plano["refusal_reason"] = (
            "Não posso expor CPF, telefone pessoal ou e-mail pessoal."
        )
    pede_previsao = bool(
        re.search(r"\b(?:sera|previsao|prever|preveja)\b", texto)
        and re.search(r"valor medio|media das contratacoes", texto)
    )
    if pede_previsao:
        plano["is_refusal"] = True
        plano["tipo_recusa"] = "limite_de_escopo"
        plano["refusal_reason"] = (
            "Este executor consulta registros disponíveis; "
            "não possui um modelo validado de previsão de valores futuros. "
            "Não posso fornecer essa previsão com segurança."
        )
    if plano["is_refusal"]:
        plano.update(
            bases=[],
            estrategia="recusa",
            operacao="recusar",
        )
        return plano
    if _solicita_calculo_media(texto):
        plano.update(
            estrategia="esclarecimento",
            operacao="esclarecer",
            necessita_esclarecimento=True,
            pergunta_esclarecimento=(
                "O cálculo de médias monetárias, incluindo preço por quilo "
                "e média ponderada, ainda não está implementado neste executor. "
                "Não posso substituir esse cálculo por trechos documentais. "
                "Você deseja uma contagem ou listagem dos registros disponíveis? "
                "Para preço por quilo, também seria necessário definir valores, "
                "quantidades e unidades compatíveis."
            ),
        )
        return plano

    if len(_extrair_ufs_explicitas(pergunta)) > 1:
        plano.update(
            estrategia="esclarecimento",
            operacao="esclarecer",
            necessita_esclarecimento=True,
            pergunta_esclarecimento=(
                "Informe uma única UF para esta consulta. "
                "A combinação de várias UFs ainda não está implementada."
            ),
        )
        return plano

    from src.aggregate_planning import planejar_agregada

    plano_agregado = planejar_agregada(texto, plano)
    if plano_agregado is not None:
        return plano_agregado

    def esclarecer(mensagem):
        plano.update(
            estrategia="esclarecimento",
            operacao="esclarecer",
            necessita_esclarecimento=True,
            pergunta_esclarecimento=mensagem,
        )
        return plano
    menciona_contratacao, contar, listar = _identificar_intencao_estruturada(
        texto
    )
    # Pedidos explícitos sobre registros não dependem de o LLM
    # ter incluído a rota estruturada. Preserva as rotas documentais.
    pede_registros = bool(re.search(
        r"\b(?:quantos|quantas|(?:total|numero|quantidade)\s+de)"
        r"\s+(?:contratos|contratacoes)\b"
        r"|\b(?:liste|listar|relacione)\s+(?:(?:os|as)\s+)?"
        r"(?:contratos|contratacoes)\b"
        r"|\bquais\s+(?:(?:os|as)\s+)?(?:contratos|contratacoes)\b",
        texto,
    ))
    tem_recorte_de_dados = bool(re.search(
        r"\bano da compra\b"
        r"|\b(?:na|da|sobre a)\s+base\b"
        r"|\bpublicad[oa]s?\b",
        texto,
    ))
    if (
        pede_registros
        and tem_recorte_de_dados
        and "estruturada" not in rotas
    ):
        rotas = [*rotas, "estruturada"]
        plano["bases"] = list(rotas)

    rotas_recuperacao = _rotas_de_recuperacao(rotas)
    tem_rota_estruturada = "estruturada" in rotas
    # PCA segue o fluxo já existente; não entra na combinação nesta etapa.
    if _eh_consulta_pca(texto):
        return plano
    from src.query_decomposition import extrair_pedido_documental

    pedido_documental = extrair_pedido_documental(pergunta)
    tarefa_estruturada = (
        tem_rota_estruturada
        and menciona_contratacao
        and (contar or listar)
    )
    consulta_combinada = bool(
        tarefa_estruturada
        and rotas_recuperacao
        and pedido_documental
    )
    if tarefa_estruturada and not pedido_documental:
        # Uma rota sugerida pelo LLM não cria outra tarefa para o usuário.
        rotas_recuperacao = []
    # Consultas documentais abertas continuam no RAG híbrido.
    if rotas_recuperacao and not consulta_combinada:
        return plano
    if not menciona_contratacao or not (contar or listar):
        return plano
    if contar and listar:
        return esclarecer(
            "Você quer apenas o total ou também uma listagem paginada?"
        )
    if re.search(
        r"\b(?:media|soma|percentual|agrupad[oa]s?)\b|por modalidade",
        texto,
    ):
        return esclarecer(
            "Este executor ainda oferece contagem e listagem simples. "
            "Qual dessas operações você deseja?"
        )
    if re.search(
        r"\b(?:atualizacao|assinad[oa]s?|assinatura)\b",
        texto,
    ):
        return esclarecer(
            "Filtros de atualização e assinatura ainda não estão implementados."
        )
    if (
        re.search(r"\b(?:publicad[oa]s?|publicacao)\b", texto)
        and periodo_publicacao is None
    ):
        return esclarecer(
            "Informe um único mês de publicação, por exemplo "
            "'em março de 2026'. Outros intervalos ainda exigem esclarecimento."
        )
    if re.search(r"\b(?:orgao|cnpj|situacao|vigencia)\b", texto):
        return esclarecer(
            "Esse critério ainda precisa ser conectado ao planejamento. "
            "Informe uma consulta com município, UF, ano da compra "
            "ou valor estimado/homologado."
        )
    filtros_router = analise.get("filters") or {}
    filtros = {
        campo: filtros_router[campo]
        for campo in ("uf", "municipio", "modalidade", "fornecedor")
        if filtros_router.get(campo) not in (None, "")
    }
    # Campos solicitados para exibição não são filtros.
    texto_criterios = re.split(
        r"\b(?:apenas|somente)\b",
        texto,
        maxsplit=1,
    )[0]
    # Não executar uma consulta mais ampla se o modelo omitir filtros.
    if (
        re.search(
            r"\bmunicipio\s+(?:de|do|da)\s+\S+",
            texto_criterios,
        )
        and not filtros.get("municipio")
    ):
        return esclarecer(
            "Qual município deve ser utilizado? "
            "Não consegui identificar esse filtro com segurança."
        )
    menciona_limite = bool(
        re.search(
            r"acima de|abaixo de|mais de|menos de|"
            r"superior|inferior|no minimo|no maximo|"
            r"pelo menos|ate\s+r\$",
            texto,
        )
    )
    if menciona_limite and not any(
        filtros_router.get(campo) is not None
        for campo in ("valor_minimo", "valor_maximo")
    ):
        return esclarecer(
            "Qual limite de valor deve ser aplicado? "
            "Não consegui extrair esse critério com segurança."
        )
    # O ano de uma referência legal não é um período da compra.
    texto_periodo_compra = re.sub(
        r"\b(?:lei(?:\s+complementar)?|decreto|resolucao|portaria)"
        r"\s*(?:n[º°o.]?\s*)?\d[\d.]*\s*/\s*\d{4}\b",
        "",
        texto,
    )
    anos = re.findall(r"\b20\d{2}\b", texto_periodo_compra)
    if len(set(anos)) > 1:
        return esclarecer(
            "Você deseja consultar qual ano da compra? "
            "Intervalos de anos ainda não estão implementados."
        )
    if anos and periodo_publicacao is None:
        filtros["ano_compra"] = int(anos[0])
    if periodo_publicacao is not None:
        filtros.update(periodo_publicacao)
        if re.search(r"\bpregao(?:\s*-\s*|\s+)eletronico\b", texto):
            # Usa o código original, evitando variações do nome da modalidade.
            filtros["modalidade_id"] = 6
            filtros.pop("modalidade", None)
    for campo in ("valor_minimo", "valor_maximo"):
        valor = filtros_router.get(campo)
        if valor is not None:
            filtros[campo] = valor
    tem_limite_valor = any(
        campo in filtros
        for campo in ("valor_minimo", "valor_maximo")
    )
    campo_valor = None
    if tem_limite_valor:
        estimado = "estimado" in texto
        homologado = "homologado" in texto
        if estimado == homologado:
            return esclarecer(
                "O limite deve ser aplicado ao valor estimado "
                "ou ao valor homologado?"
            )
        campo_valor = (
            "valor_estimado" if estimado else "valor_homologado"
        )
    criterio_objeto = None
    if "tecnologia" in texto:
        if not isinstance(criterio_tecnologia, dict):
            return esclarecer(
                "Qual critério documentado deve identificar "
                "as contratações de tecnologia?"
            )
        from src.technology_classifier import VERSAO_CRITERIO

        if criterio_tecnologia.get("implementacao") == VERSAO_CRITERIO:
            descricao_contextual = criterio_tecnologia.get(
                "regra_principal"
            )
            if (
                not isinstance(descricao_contextual, str)
                or not descricao_contextual.strip()
            ):
                raise ValueError(
                    "Informe a regra principal do critério contextual."
                )

            tipo_tic = (
                "servico_proposto"
                if re.search(r"\bservicos? de tecnologia\b", texto)
                else "todos"
            )

            criterio_objeto = (
                descricao_contextual.strip()
                + " Aplicação operacional: "
                + VERSAO_CRITERIO
                + ". Total de classificações propostas; "
                "casos ambíguos permanecem para revisão."
            )

            plano["criterio_tecnologia"] = {
                "implementacao": VERSAO_CRITERIO,
                "descricao": criterio_objeto,
                "tipo": tipo_tic,
            }
        else:
            # O critério contextual exige decisões rastreáveis;
            # termos indicativos não equivalem a classificação validada.
            criterio_contextual = any(
                campo in criterio_tecnologia
                for campo in (
                    "regra_principal",
                    "termos_indicativos",
                    "termos_ambiguos",
                    "regras",
                )
            )
            if criterio_contextual:
                return esclarecer(
                    "O critério contextual de TIC exige classificação "
                    "rastreável dos registros. A classificação disponível "
                    "ainda é preliminar e não permite informar um total "
                    "validado. Você deseja utilizar um critério textual "
                    "explicitamente documentado ou revisar a classificação?"
                )

            termos = criterio_tecnologia.get("termos")
            descricao = criterio_tecnologia.get("descricao")
            if (
                not isinstance(termos, list)
                or not termos
                or not all(isinstance(t, str) and t.strip() for t in termos)
                or not isinstance(descricao, str)
                or not descricao.strip()
            ):
                raise ValueError("Critério de tecnologia inválido.")
            filtros["objeto_termos"] = termos
            criterio_objeto = descricao
    elif re.search(
        r"\b(?:de|sobre|envolvem|relacionad[oa]s? a)\s+"
        r"(?:servicos? de|software|informatica|material|reparo)",
        texto,
    ):
        return esclarecer(
            "Informe o critério textual documentado para filtrar "
            "o objeto da contratação."
        )
    campos = None
    if listar:
        campos = _extrair_campos_saida(texto_completo)
        if re.search(r"\b(?:apenas|somente)\b", texto) and not campos:
            return esclarecer(
                "Quais campos você deseja exibir na listagem?"
            )
    paginacao = {"pagina": 1, "tamanho_pagina": 20}
    if listar:
        try:
            paginacao = _extrair_paginacao_explicita(texto)
        except ValueError as erro:
            return esclarecer(str(erro))
    if consulta_combinada:
        estrategia = "combinada"
        bases = _bases_da_consulta_combinada(
            rotas,
            rotas_recuperacao,
        )
    else:
        estrategia = "consulta_estruturada"
        bases = ["estruturada"]
    plano.update(
        bases=bases,
        estrategia=estrategia,
        operacao="listar" if listar else "contar",
        filtros=filtros,
        campos=campos,
        pagina=paginacao["pagina"],
        tamanho_pagina=paginacao["tamanho_pagina"],
        campo_valor=campo_valor,
        criterio_objeto=criterio_objeto,
        minimo_inclusivo=not bool(
            re.search(r"acima de|mais de|superior", texto)
        ),
        maximo_inclusivo=not bool(
            re.search(r"abaixo de|menos de|inferior", texto)
        ),
        rotas_recuperacao=(
            rotas_recuperacao if consulta_combinada else []
        ),
    )
    return plano


# Campos de apresentação não definem contagem ou filtros.
CAMPOS_SAIDA_ALIASES.update({
    "id_pncp": (
        "id", "identificador", "numero de controle pncp",
        "numero pncp", "id pncp",
    ),
    "orgao": ("orgao",),
    "modalidade": ("modalidade",),
    "data_publicacao": ("data de publicacao", "data_publicacao"),
})


def _separar_campos_de_exibicao(texto):
    """Remove da intenção somente cláusulas explícitas de campos conhecidos."""
    nomes = {
        nome
        for aliases in CAMPOS_SAIDA_ALIASES.values()
        for nome in aliases
    }

    def substituir(achado):
        campos = [
            parte.strip()
            for parte in re.split(r",|\s+e\s+", achado.group(1))
            if parte.strip()
        ]
        if campos and all(campo in nomes for campo in campos):
            return ""
        # Preserva termos desconhecidos e critérios adicionais.
        return achado.group(0)

    return re.sub(
        r"\b(?:mostre|exiba|apresente)\s+(?:apenas|somente)\s+"
        r"([^.;?]+)(?:[.;?]|$)",
        substituir,
        texto,
    ).strip()

if __name__ == "__main__":
    consulta = input("Digite uma pergunta: ")
    saida = analisar_consulta(consulta)
    print(json.dumps(saida, ensure_ascii=False, indent=2))
