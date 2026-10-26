"""
teste_router.py

Testes unitários para repositorio1/src/router.py.

IMPORTANTE:
- O router.py original NÃO é alterado.
- analisar_consulta() retorna dict.
- Os testes são offline e usam um cliente LLM falso.
"""

import json
from types import SimpleNamespace

import pytest

from src.router import analisar_consulta


class FakeCompletions:
    """Simula client.chat.completions.create()."""

    def __init__(
        self,
        conteudo=None,
        erro=None,
        prompt_tokens=100,
        completion_tokens=30,
        total_tokens=130,
    ):
        self.conteudo = conteudo
        self.erro = erro
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def create(self, **kwargs):
        if self.erro is not None:
            raise self.erro

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.conteudo)
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                total_tokens=self.total_tokens,
            ),
        )


class FakeClient:
    """Cliente falso compatível com o cliente usado pelo router."""

    def __init__(
        self,
        conteudo=None,
        erro=None,
        prompt_tokens=100,
        completion_tokens=30,
        total_tokens=130,
    ):
        self.chat = SimpleNamespace(
            completions=FakeCompletions(
                conteudo=conteudo,
                erro=erro,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        )


def resposta_router(
    routes,
    filters=None,
    is_refusal=False,
    refusal_reason=None,
    justification="Rota selecionada para atender à consulta.",
):
    """Monta o JSON simulado retornado pelo LLM roteador."""

    return json.dumps(
        {
            "routes": routes,
            "filters": filters or {},
            "is_refusal": is_refusal,
            "refusal_reason": refusal_reason,
            "justification": justification,
        },
        ensure_ascii=False,
    )


# ============================================================
# VALIDAÇÃO DA ENTRADA
# ============================================================

def test_pergunta_vazia_deve_falhar():
    with pytest.raises(ValueError):
        analisar_consulta("")


def test_pergunta_apenas_espacos_deve_falhar():
    with pytest.raises(ValueError):
        analisar_consulta("   ")


# ============================================================
# ROTAS
# ============================================================

def test_rota_estruturada():
    client = FakeClient(
        resposta_router(
            routes=["estruturada"],
            filters={"uf": "RJ", "ano": 2025},
        )
    )

    resultado = analisar_consulta(
        "Quais contratos de tecnologia foram celebrados no RJ em 2025?",
        client=client,
    )

    assert resultado["routes"] == ["estruturada"]
    assert resultado["filters"]["uf"] == "RJ"
    assert resultado["filters"]["ano"] == 2025
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False
    assert resultado["stage"] == "roteamento"


def test_rota_normativa():
    client = FakeClient(
        resposta_router(
            routes=["normativa"],
            justification="A pergunta solicita regra da Lei 14.133/2021.",
        )
    )

    resultado = analisar_consulta(
        "O que a Lei 14.133/2021 estabelece sobre pregão?",
        client=client,
    )

    assert resultado["routes"] == ["normativa"]
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False


def test_rota_conversacional():
    client = FakeClient(
        resposta_router(
            routes=["conversacional"],
            justification="A consulta busca informação em atas ou comunicações.",
        )
    )

    resultado = analisar_consulta(
        "O que consta na ata de registro de preços?",
        client=client,
    )

    assert resultado["routes"] == ["conversacional"]
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False


def test_rota_agregada():
    client = FakeClient(
        resposta_router(
            routes=["agregada"],
            filters={"uf": "RJ", "ano": 2025},
        )
    )

    resultado = analisar_consulta(
        "Qual foi o valor médio contratado no RJ em 2025?",
        client=client,
    )

    assert resultado["routes"] == ["agregada"]
    assert resultado["filters"]["uf"] == "RJ"
    assert resultado["filters"]["ano"] == 2025
    assert resultado["router_fallback"] is False


def test_multiplas_rotas():
    client = FakeClient(
        resposta_router(
            routes=["agregada", "estruturada"],
            filters={"uf": "RJ", "ano": 2025},
        )
    )

    resultado = analisar_consulta(
        "Qual foi o valor médio por quilo de arroz contratado "
        "por municípios do RJ em 2025 e em quais modalidades?",
        client=client,
    )

    assert resultado["routes"] == ["agregada", "estruturada"]
    assert len(resultado["routes"]) == 2


# ------------------------------------------------------------
# CROSS-SOURCE: consultas que exigem mais de uma base ao mesmo
# tempo. O router.py já suporta isso (ver _normalizar_rotas),
# mas faltava um teste explícito cobrindo cada combinação citada
# no checklist do Sprint.
# ------------------------------------------------------------

def test_cross_source_normativa_e_estruturada():
    client = FakeClient(
        resposta_router(
            routes=["normativa", "estruturada"],
            filters={"uf": "RJ"},
            justification=(
                "A pergunta pede a regra de participação (normativa) "
                "e também contratos abertos (estruturada)."
            ),
        )
    )

    resultado = analisar_consulta(
        "Sou MEI, posso participar de pregão eletrônico? "
        "Existe algum contrato aberto no RJ agora?",
        client=client,
    )

    assert set(resultado["routes"]) == {"normativa", "estruturada"}
    assert len(resultado["routes"]) == 2
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False


def test_cross_source_agregada_e_estruturada():
    client = FakeClient(
        resposta_router(
            routes=["agregada", "estruturada"],
            filters={"uf": "RJ", "ano": 2025},
        )
    )

    resultado = analisar_consulta(
        "Quantos contratos foram assinados por modalidade em 2025 no RJ?",
        client=client,
    )

    assert set(resultado["routes"]) == {"agregada", "estruturada"}
    assert len(resultado["routes"]) == 2


def test_cross_source_normativa_agregada_e_estruturada():
    client = FakeClient(
        resposta_router(
            routes=["normativa", "agregada", "estruturada"],
            filters={"uf": "RJ", "ano": 2025},
            justification=(
                "A pergunta pede a norma aplicável, uma média (agregada) "
                "e os contratos que a compõem (estruturada)."
            ),
        )
    )

    resultado = analisar_consulta(
        "Pela Lei 14.133/2021, qual o valor médio permitido por dispensa "
        "de licitação, e quais contratos do RJ em 2025 usaram essa regra?",
        client=client,
    )

    assert set(resultado["routes"]) == {
        "normativa",
        "agregada",
        "estruturada",
    }
    assert len(resultado["routes"]) == 3
    assert resultado["is_refusal"] is False
    assert resultado["router_fallback"] is False


def test_remove_rotas_invalidas_e_duplicadas():
    client = FakeClient(
        resposta_router(
            routes=[
                "estruturada",
                "ESTRUTURADA",
                "rota_invalida",
                "normativa",
            ]
        )
    )

    resultado = analisar_consulta(
        "Consulta de teste.",
        client=client,
    )

    assert resultado["routes"] == ["estruturada", "normativa"]


def test_rota_padrao_quando_llm_nao_define_rota():
    client = FakeClient(
        resposta_router(
            routes=[],
            is_refusal=False,
        )
    )

    resultado = analisar_consulta(
        "Consulta sem rota definida.",
        client=client,
    )

    assert resultado["routes"] == ["estruturada"]
    assert resultado["router_fallback"] is False


# ============================================================
# FILTROS
# ============================================================

def test_extracao_de_filtros_retornados_pelo_llm():
    client = FakeClient(
        resposta_router(
            routes=["estruturada"],
            filters={
                "uf": "RJ",
                "ano": 2025,
                "valor_minimo": 500000,
                "valor_maximo": None,
                "modalidade": "Pregão - Eletrônico",
                "municipio": "Rio de Janeiro",
                "fornecedor": "Exemplo Tecnologia Ltda.",
            },
        )
    )

    resultado = analisar_consulta(
        "Contratos da Exemplo Tecnologia Ltda. no Rio de Janeiro, "
        "RJ, em 2025, acima de R$ 500 mil, por pregão eletrônico.",
        client=client,
    )

    filtros = resultado["filters"]

    assert filtros["uf"] == "RJ"
    assert filtros["ano"] == 2025
    assert filtros["valor_minimo"] == 500000
    assert filtros["valor_maximo"] is None
    assert filtros["modalidade"] == "Pregão - Eletrônico"
    assert filtros["municipio"] == "Rio de Janeiro"
    assert filtros["fornecedor"] == "Exemplo Tecnologia Ltda."


# ------------------------------------------------------------
# FILTRO NUMÉRICO: "contratos acima de R$ 500 mil" e variações.
# valor_minimo/valor_maximo não passam pela checagem de "aparece
# literalmente no texto" (o LLM converte "500 mil" em 500000),
# então o que se valida aqui é que o número chega correto tanto
# quando o LLM responde quanto no fallback por regex.
# ------------------------------------------------------------

def test_filtro_numerico_valor_minimo_via_llm():
    client = FakeClient(
        resposta_router(
            routes=["estruturada"],
            filters={
                "uf": "RJ",
                "valor_minimo": 500000,
                "valor_maximo": None,
            },
        )
    )

    resultado = analisar_consulta(
        "Quais contratos de tecnologia ficaram acima de R$ 500 mil?",
        client=client,
    )

    assert resultado["routes"] == ["estruturada"]
    assert resultado["filters"]["valor_minimo"] == 500000
    assert resultado["filters"]["valor_maximo"] is None


def test_filtro_numerico_valor_maximo_via_llm():
    client = FakeClient(
        resposta_router(
            routes=["estruturada"],
            filters={
                "uf": "RJ",
                "valor_minimo": None,
                "valor_maximo": 200000,
            },
        )
    )

    resultado = analisar_consulta(
        "Quais contratos ficaram abaixo de R$ 200 mil?",
        client=client,
    )

    assert resultado["filters"]["valor_minimo"] is None
    assert resultado["filters"]["valor_maximo"] == 200000


def test_fallback_extrai_valor_minimo_em_mil():
    client = FakeClient(erro=RuntimeError("Falha simulada"))

    resultado = analisar_consulta(
        "Quais contratos de tecnologia no RJ em 2025 acima de R$ 500 mil?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["filters"]["valor_minimo"] == 500000.0


def test_fallback_extrai_valor_minimo_em_milhoes():
    client = FakeClient(erro=RuntimeError("Falha simulada"))

    resultado = analisar_consulta(
        "Contratos superiores a 2 milhões de reais no RJ.",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["filters"]["valor_minimo"] == 2_000_000.0


# ============================================================
# SEGURANÇA / RECUSA
# ============================================================

def test_recusa():
    client = FakeClient(
        resposta_router(
            routes=[],
            is_refusal=True,
            refusal_reason="Solicitação envolve dados bancários protegidos.",
            justification="A consulta solicita informação sensível.",
        )
    )

    resultado = analisar_consulta(
        "Informe os dados bancários do fornecedor.",
        client=client,
    )

    assert resultado["is_refusal"] is True
    assert resultado["refusal_reason"] is not None
    assert resultado["routes"] == []
    assert resultado["router_fallback"] is False


# ============================================================
# METADADOS DO ROTEAMENTO
# ============================================================

def test_tokens_do_roteador():
    client = FakeClient(
        resposta_router(routes=["estruturada"]),
        prompt_tokens=120,
        completion_tokens=40,
        total_tokens=160,
    )

    resultado = analisar_consulta(
        "Quais contratos existem?",
        client=client,
    )

    assert resultado["tokens"]["prompt"] == 120
    assert resultado["tokens"]["completion"] == 40
    assert resultado["tokens"]["total"] == 160


def test_query_original_preservada():
    pergunta = "Quais contratos de tecnologia existem no RJ?"

    client = FakeClient(
        resposta_router(
            routes=["estruturada"],
            filters={"uf": "RJ"},
        )
    )

    resultado = analisar_consulta(
        pergunta,
        client=client,
    )

    assert resultado["query"] == pergunta
    assert resultado["query_id"]
    assert resultado["query_id"].startswith("q_")
    assert resultado["stage"] == "roteamento"
    assert resultado["modelo"]


def test_latencia_registrada():
    client = FakeClient(
        resposta_router(routes=["estruturada"])
    )

    resultado = analisar_consulta(
        "Quais contratos existem?",
        client=client,
    )

    assert "latencia_ms" in resultado
    assert isinstance(resultado["latencia_ms"], (int, float))
    assert resultado["latencia_ms"] >= 0


# ============================================================
# FALLBACK
# ============================================================

def test_fallback_quando_llm_falha():
    client = FakeClient(
        erro=RuntimeError("Falha simulada do LLM")
    )

    resultado = analisar_consulta(
        "Quais contratos de tecnologia no RJ em 2025 acima de R$ 500 mil?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["router_error"] == "Falha simulada do LLM"
    assert resultado["is_refusal"] is False
    assert len(resultado["routes"]) >= 1


def test_fallback_extrai_ano():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Quais contratos de tecnologia foram publicados em 2025?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["filters"]["ano"] == 2025


def test_fallback_define_uf_rj():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Quais contratos foram publicados no RJ em 2025?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["filters"]["uf"] == "RJ"


def test_fallback_possui_rota_valida():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Liste as contratações disponíveis.",
        client=client,
    )

    rotas_validas = {
        "normativa",
        "estruturada",
        "conversacional",
        "agregada",
    }

    assert resultado["router_fallback"] is True
    assert resultado["routes"]
    assert all(
        rota in rotas_validas
        for rota in resultado["routes"]
    )


def test_fallback_mei_somente_normativa():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Sou MEI, posso participar de pregão eletrônico?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["routes"] == ["normativa"]


def test_fallback_contratacao_somente_estruturada():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Existe alguma contratação relacionada "
        "a material de escritório?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert resultado["routes"] == ["estruturada"]


def test_fallback_cross_source_normativa_estruturada():
    client = FakeClient(
        erro=RuntimeError("Falha simulada")
    )

    resultado = analisar_consulta(
        "Sou MEI, posso participar de pregão eletrônico? "
        "Existe alguma contratação relacionada "
        "a material de escritório?",
        client=client,
    )

    assert resultado["router_fallback"] is True
    assert set(resultado["routes"]) == {
        "normativa",
        "estruturada",
    }
