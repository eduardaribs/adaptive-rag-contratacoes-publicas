"""Seleção controlada do novo caminho analítico da interface."""

import os
import re
import unicodedata
from contextvars import ContextVar

from src.obs import observar_etapa

_CONSULTA_DOCUMENTAL = ContextVar("consulta_documental_em_andamento", default=False)


def deve_usar_analitica(pergunta, consulta):
    """Seleciona candidato por fonte; a intenção é decidida pelo interpretador."""
    if _CONSULTA_DOCUMENTAL.get():
        return False
    if os.getenv("RAG_ANALYTICAL_ENABLED", "false").lower() != "true":
        return False
    if os.getenv("RAG_DEMO_OFFLINE", "false").lower() == "true":
        return False

    plano = consulta.get("plano") or {}
    if consulta.get("is_refusal") or plano.get("is_refusal"):
        return False
    if consulta.get("estrategia") == "recusa":
        return False

    # A verificação de vínculos existente continua no executor próprio.
    if (
        consulta.get("operacao") == "resumir_itens_vinculos"
        or plano.get("operacao") == "resumir_itens_vinculos"
    ):
        return False

    texto = "".join(
        c for c in unicodedata.normalize("NFD", pergunta.casefold())
        if unicodedata.category(c) != "Mn"
    )
    fonte_identificada = bool(
        re.search(r"\bpe\s*038\s*/\s*26\s*/\s*2026\b", texto)
        or re.search(r"\bpca\b|plano de contratacoes anual", texto)
    )
    # A rota agregada não identifica qual arquivo atende ao pedido.
    # O novo catálogo só pode ser usado com uma fonte reconhecida.
    # A operação permanece a cargo do interpretador, sem lista de verbos.
    return fonte_identificada


def tentar_analitica(
    pergunta, consulta, *, run_id, on_progress=None, top_k=3
):
    if not deve_usar_analitica(pergunta, consulta):
        return None

    from app.analytical_adapter import executar_analitica_interface

    plano = consulta.get("plano") or {}
    query_id = consulta.get("query_id") or plano.get("query_id")

    with observar_etapa(
        run_id=run_id,
        query_id=query_id,
        stage="roteamento",
        input_data={
            "tipo": "selecao_caminho_analitico",
            "pergunta": pergunta,
        },
    ) as evento:
        evento["output"] = {
            "destino": "adaptador_analitico",
            "estrategia_anterior": (
                consulta.get("estrategia") or plano.get("estrategia")
            ),
        }

    def executar_documental(pedido):
        token = _CONSULTA_DOCUMENTAL.set(True)
        try:
            from app.pipeline_adapter import executar_pipeline
            return executar_pipeline(pedido, top_k=top_k)
        finally:
            _CONSULTA_DOCUMENTAL.reset(token)

    resultado = executar_analitica_interface(
        pergunta,
        run_id=run_id,
        query_id=query_id,
        on_progress=on_progress,
        documental_executor=executar_documental,
    )

    interpretacao = (resultado or {}).get("interpretacao_analitica") or {}
    bases = set(consulta.get("routes") or plano.get("bases") or [])
    estrategia = consulta.get("estrategia") or plano.get("estrategia")
    if (
        resultado is not None
        and resultado.get("necessita_esclarecimento")
        and interpretacao.get("tipo") == "esclarecimento"
        and interpretacao.get("tentativas", 0) > 0
        and estrategia == "recuperacao_hibrida"
        and bases and bases.issubset({"normativa", "conversacional"})
        and consulta.get("executado", True)
    ):
        with observar_etapa(
            run_id=run_id, query_id=query_id, stage="validacao",
            input_data={"tipo": "preservacao_caminho_documental"},
        ) as evento:
            evento["output"] = {
                "mensagem_planejador_nao_usada_como_resposta": True,
                "destino": "recuperacao_documental_existente",
            }
        return None
    return resultado
