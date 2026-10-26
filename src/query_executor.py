"""Executa planos explícitos de consulta.

Mantém compatibilidade com as estratégias existentes e adiciona suporte à
execução combinada de consulta estruturada + recuperação híbrida.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from src.structured_query import carregar_base, consultar_registros


_ESTRATEGIAS_VALIDAS = {
    'combinada',
    'consulta_agregada',
    'consulta_estruturada',
    'recuperacao_hibrida',
}

_OPERACOES_ESTRUTURADAS = {"contar", "listar"}


def _obter_query_id(
    plano: dict[str, Any],
    analise_pronta: dict[str, Any] | None,
) -> str:
    """Reutiliza o query_id existente ou cria um novo."""
    return (
        (analise_pronta or {}).get("query_id")
        or plano.get("query_id")
        or f"q_{uuid.uuid4().hex[:8]}"
    )


def _validar_operacao_estruturada(plano: dict[str, Any]) -> str:
    operacao = plano.get("operacao")
    if operacao not in _OPERACOES_ESTRUTURADAS:
        raise ValueError("Operação estruturada inválida.")
    return operacao


def _argumentos_consulta_estruturada(
    plano: dict[str, Any],
) -> dict[str, Any]:
    """Centraliza os parâmetros enviados ao structured_query."""
    return {
        "operacao": plano.get("operacao"),
        "filtros": plano.get("filtros", {}),
        "campos": plano.get("campos"),
        "pagina": plano.get("pagina", 1),
        "tamanho_pagina": plano.get("tamanho_pagina", 20),
        "campo_valor": plano.get("campo_valor"),
        "minimo_inclusivo": plano.get("minimo_inclusivo", True),
        "maximo_inclusivo": plano.get("maximo_inclusivo", True),
        "criterio_objeto": plano.get("criterio_objeto"),
        "criterio_tecnologia": plano.get("criterio_tecnologia"),
    }


def _executar_estruturada(
    pergunta: str,
    plano: dict[str, Any],
    *,
    base: list[dict[str, Any]] | None,
    analise_pronta: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    """Executa a parte determinística sobre a base estruturada."""
    from src import obs

    if plano.get("estrategia") == "consulta_estruturada":
        if plano.get("bases") != ["estruturada"]:
            raise ValueError(
                "A consulta estruturada exige apenas a base estruturada."
            )

    operacao = _validar_operacao_estruturada(plano)
    run_id = run_id or obs.novo_run_id()
    query_id = _obter_query_id(plano, analise_pronta)
    inicio_execucao = time.perf_counter()
    argumentos = _argumentos_consulta_estruturada(plano)

    with obs.observar_etapa(
        run_id=run_id,
        query_id=query_id,
        stage="consulta_estruturada",
        input_data=argumentos,
    ) as observacao:
        registros = carregar_base() if base is None else base
        resultado = consultar_registros(registros, **argumentos)

        observacao["output"] = {
            "operacao": resultado["operacao"],
            "filtros_aplicados": resultado["filtros_aplicados"],
            "total_base": resultado["total_base"],
            "total": resultado["total"],
            "pagina": resultado["pagina"],
            "tamanho_pagina": resultado["tamanho_pagina"],
            "total_paginas": resultado["total_paginas"],
            "quantidade_retornada": len(resultado["registros"]),
            "campos": resultado["campos"],
            "resumo_tecnologia": resultado.get("resumo_tecnologia"),
            "registros_sem_publicacao": resultado.get(
                "registros_sem_publicacao", 0
            ),
        }

    return {
        **resultado,
        "query": pergunta.strip(),
        "query_id": query_id,
        "run_id": run_id,
        "routes": ["estruturada"],
        "estrategia": "consulta_estruturada",
        "latencia_ms": round(
            (time.perf_counter() - inicio_execucao) * 1000,
            2,
        ),
    }


def _montar_analise_recuperacao(
    plano: dict[str, Any],
    analise_pronta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Separa rotas e filtros documentais da consulta estruturada."""
    rotas = plano.get("rotas_recuperacao")
    if not rotas:
        rotas = [
            rota
            for rota in plano.get("bases", [])
            if rota != "estruturada"
        ]

    if analise_pronta is None:
        return None

    analise_recuperacao = dict(analise_pronta)
    if rotas:
        analise_recuperacao["routes"] = list(dict.fromkeys(rotas))

    filtros = dict(analise_pronta.get("filters") or {})

    if plano.get("estrategia") == "combinada":
        if "filtros_recuperacao" in plano:
            filtros_documentais = plano["filtros_recuperacao"]
            if not isinstance(filtros_documentais, dict):
                raise ValueError(
                    "filtros_recuperacao deve ser um dicionário."
                )
            filtros = dict(filtros_documentais)

        elif set(rotas) == {"normativa"}:
            # Estes filtros descrevem as contratações, não a norma.
            filtros_estruturados = {
                "uf", "municipio", "ano", "ano_compra",
                "valor_minimo", "valor_maximo",
                "modalidade", "modalidade_id",
                "fornecedor", "orgao", "objeto_termos",
                "data_inicial", "data_final",
            }
            filtros = {
                campo: valor
                for campo, valor in filtros.items()
                if campo not in filtros_estruturados
            }

    analise_recuperacao["filters"] = filtros
    return analise_recuperacao



def _executar_hibrida(
    pergunta: str,
    plano: dict[str, Any],
    *,
    top_k: int,
    fetch_k: int,
    client,
    recuperador: Callable | None,
    analise_pronta: dict[str, Any] | None,
    run_id: str | None,
    validar_operacao: bool = True,
) -> dict[str, Any]:
    """Executa a recuperação híbrida, com suporte a recuperador injetado."""
    if validar_operacao and plano.get("operacao") != "buscar":
        raise ValueError("A recuperação híbrida exige operação buscar.")

    if recuperador is None:
        from src.retrieve import recuperar_evidencias

        recuperador = recuperar_evidencias

    argumentos: dict[str, Any] = {
        "pergunta": pergunta.strip(),
        "top_k": top_k,
        "fetch_k": fetch_k,
        "client": client,
    }

    if analise_pronta is not None:
        argumentos["analise_pronta"] = analise_pronta
    if run_id is not None:
        argumentos["run_id"] = run_id

    resultado = recuperador(**argumentos)

    return {
        **resultado,
        "estrategia": "recuperacao_hibrida",
        "operacao": "buscar",
    }


def _executar_combinada(
    pergunta: str,
    plano: dict[str, Any],
    *,
    base: list[dict[str, Any]] | None,
    top_k: int,
    fetch_k: int,
    client,
    recuperador: Callable | None,
    analise_pronta: dict[str, Any] | None,
    run_id: str | None,
) -> dict[str, Any]:
    """Executa consulta estruturada e recuperação híbrida na mesma pergunta."""
    from src import obs

    bases = plano.get("bases", [])
    if "estruturada" not in bases:
        raise ValueError(
            "A estratégia combinada exige a base estruturada."
        )

    rotas_recuperacao = plano.get("rotas_recuperacao") or [
        rota for rota in bases if rota != "estruturada"
    ]
    rotas_recuperacao = list(dict.fromkeys(rotas_recuperacao))

    if not rotas_recuperacao:
        raise ValueError(
            "A estratégia combinada exige ao menos uma rota de recuperação."
        )

    _validar_operacao_estruturada(plano)

    run_id = run_id or obs.novo_run_id()
    query_id = _obter_query_id(plano, analise_pronta)
    inicio_execucao = time.perf_counter()

    plano_estruturado = {
        **plano,
        "bases": ["estruturada"],
        "estrategia": "consulta_estruturada",
        "query_id": query_id,
    }

    analise_recuperacao = _montar_analise_recuperacao(
        plano,
        analise_pronta,
    )

    if analise_recuperacao is not None:
        analise_recuperacao["query_id"] = query_id

    resultado_estruturado = _executar_estruturada(
        pergunta,
        plano_estruturado,
        base=base,
        analise_pronta=analise_pronta,
        run_id=run_id,
    )

    from src.query_decomposition import extrair_pedido_documental

    pergunta_documental = extrair_pedido_documental(pergunta) or pergunta
    if analise_recuperacao is not None:
        analise_recuperacao["query"] = pergunta_documental

    resultado_hibrido = _executar_hibrida(
        pergunta_documental,
        plano,
        top_k=top_k,
        fetch_k=fetch_k,
        client=client,
        recuperador=recuperador,
        analise_pronta=analise_recuperacao,
        run_id=run_id,
        validar_operacao=False,
    )

    resultado_hibrido["query_original"] = pergunta.strip()
    resultado_hibrido["query_documental"] = pergunta_documental.strip()

    evidencias = resultado_hibrido.get(
        "evidences",
        resultado_hibrido.get("evidencias", []),
    )

    return {
        "query": pergunta.strip(),
        "query_id": query_id,
        "run_id": run_id,
        "routes": list(dict.fromkeys(bases)),
        "estrategia": "combinada",
        "operacao": plano.get("operacao"),
        # Mantém os blocos completos para auditoria e depuração.
        "estruturada": resultado_estruturado,
        "hibrida": resultado_hibrido,
        # Mantém campos úteis no nível superior para reduzir impacto em
        # consumidores que já esperam total/registros/evidências diretamente.
        "total": resultado_estruturado.get("total"),
        "registros": resultado_estruturado.get("registros", []),
        "evidences": evidencias,
        "evidencias": evidencias,
        "latencia_ms": round(
            (time.perf_counter() - inicio_execucao) * 1000,
            2,
        ),
    }


def executar_plano(
    pergunta: str,
    plano: dict[str, Any],
    *,
    base: list[dict[str, Any]] | None = None,
    top_k: int = 3,
    fetch_k: int = 50,
    client=None,
    recuperador: Callable | None = None,
    analise_pronta: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Executa um plano previamente construído pelo roteador."""
    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    if not isinstance(plano, dict):
        raise ValueError("O plano deve ser um dicionário.")

    estrategia = plano.get("estrategia")
    if estrategia not in _ESTRATEGIAS_VALIDAS:
        raise ValueError(
            "Estratégia inválida. Use consulta_estruturada, "
            "recuperacao_hibrida, combinada ou consulta_agregada."
        )

    if estrategia == "consulta_agregada":
        from src import obs
        from src.aggregate_query import executar_agregada

        inicio_agregada = time.perf_counter()
        run_id = run_id or obs.novo_run_id()
        query_id = _obter_query_id(plano, analise_pronta)

        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="consulta_agregada",
            input_data={
                "operacao": plano.get("operacao"),
                "filtros": plano.get("filtros", {}),
                "recorte_fonte": plano.get("recorte_fonte"),
            },
        ) as observacao:
            resultado = executar_agregada(plano)
            observacao["output"] = {
                campo: resultado[campo]
                for campo in (
                    "operacao", "filtros_aplicados", "total_base",
                    "itens_total", "homologados", "fracassados",
                    "desertos", "valor_total_homologado",
                    "homologados_sem_valor", "total_itens",
                    "valor_total_estimado", "itens_sem_valor",
                    "soma_completa", "fontes",
                    "total_chunks_verificados",
                    "total_vinculos_complementares",
                    "fonte_corpus_verificado",
                )
                if campo in resultado
            }

        return {
            **resultado,
            "query": pergunta.strip(),
            "query_id": query_id,
            "run_id": run_id,
            "routes": ["agregada"],
            "latencia_ms": round(
                (time.perf_counter() - inicio_agregada) * 1000, 2
            ),
        }

    if estrategia == "consulta_estruturada":
        return _executar_estruturada(
            pergunta,
            plano,
            base=base,
            analise_pronta=analise_pronta,
            run_id=run_id,
        )

    if estrategia == "recuperacao_hibrida":
        return _executar_hibrida(
            pergunta,
            plano,
            top_k=top_k,
            fetch_k=fetch_k,
            client=client,
            recuperador=recuperador,
            analise_pronta=analise_pronta,
            run_id=run_id,
        )

    return _executar_combinada(
        pergunta,
        plano,
        base=base,
        top_k=top_k,
        fetch_k=fetch_k,
        client=client,
        recuperador=recuperador,
        analise_pronta=analise_pronta,
        run_id=run_id,
    )


def executar_consulta(
    pergunta,
    *,
    base=None,
    client=None,
    top_k=3,
    fetch_k=50,
    criterio_tecnologia=None,
    analise=None,
    recuperador=None,
    run_id=None,
):
    """Analisa, planeja e executa uma consulta ponta a ponta."""
    from src import obs
    from src.router import analisar_consulta, planejar_consulta

    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    run_id = run_id or obs.novo_run_id()

    if analise is None:
        analise = analisar_consulta(
            pergunta,
            client=client,
            run_id=run_id,
        )

    plano = planejar_consulta(
        pergunta,
        client=client,
        run_id=run_id,
        criterio_tecnologia=criterio_tecnologia,
        analise=analise,
    )

    if plano["is_refusal"] or plano["necessita_esclarecimento"]:
        motivo_encerramento = (
            plano.get("refusal_reason")
            if plano["is_refusal"]
            else plano.get("pergunta_esclarecimento")
        )
        with obs.observar_etapa(
            run_id=run_id,
            query_id=plano.get("query_id"),
            stage="validacao",
            input_data={"tipo": "encerramento_consulta"},
        ) as observacao:
            observacao["output"] = {
                "estrategia": plano.get("estrategia"),
                "operacao": plano.get("operacao"),
                "is_refusal": plano["is_refusal"],
                "tipo_recusa": plano.get("tipo_recusa"),
                "necessita_esclarecimento": plano["necessita_esclarecimento"],
                "motivo": motivo_encerramento,
                "consulta_bases_executada": False,
            }
        return {
            "query": pergunta,
            "query_id": plano.get("query_id"),
            "run_id": run_id,
            "plano": plano,
            "executado": False,
            "mensagem": (
                plano.get("refusal_reason")
                if plano["is_refusal"]
                else plano.get("pergunta_esclarecimento")
            ),
        }

    resultado = executar_plano(
        pergunta,
        plano,
        base=base,
        client=client,
        top_k=top_k,
        fetch_k=fetch_k,
        recuperador=recuperador,
        analise_pronta=analise,
        run_id=run_id,
    )

    if plano["estrategia"] in {
        "consulta_estruturada",
        "combinada",
    }:
        plano["query_id"] = resultado["query_id"]

    return {
        **resultado,
        "run_id": run_id,
        "plano": plano,
        "executado": True,
    }
