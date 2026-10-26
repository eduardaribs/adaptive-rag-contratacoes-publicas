"""Adapta interpretação, cálculo e resposta ao contrato da interface."""

import json
import time
import uuid
from pathlib import Path

from src import obs
from src.analytical_interpreter import interpretar_analitica
from src.analytical_sources import executar_fonte
from src.analytical_presentation import renderizar_agrupamento
from src.generate import gerar_resposta, mascarar_dados_pessoais
from src.schema import RetrievalResult, SourceEvidence


def _celula(valor):
    texto = "Não informado" if valor is None else str(valor)
    texto = mascarar_dados_pessoais(texto)
    return (
        texto.replace("\\", "\\\\")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "&#124;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _tabela_listagem(resultado):
    campos = resultado["campos"]
    registros = resultado["registros"]
    if not campos or len(campos) != len(set(campos)):
        raise ValueError("Colunas de listagem inválidas.")

    linhas = []
    for registro in registros:
        if any(campo not in registro for campo in campos):
            raise ValueError("Registro sem uma coluna solicitada.")
        linhas.append([_celula(registro[campo]) for campo in campos])

    partes = [
        "| " + " | ".join(_celula(c) for c in campos) + " |",
        "| " + " | ".join("---" for _ in campos) + " |",
    ]
    partes.extend(
        "| " + " | ".join(linha) + " |"
        for linha in linhas
    )

    if resultado.get("truncado"):
        partes.append(
            "\nExibidos "
            f"{len(linhas)} de "
            f"{resultado.get('total_resultados', resultado['total_registros'])} "
            "registros "
            "que atendem aos filtros."
        )
    if not linhas:
        partes.append("\nNenhum registro encontrado.")

    return {
        "colunas": campos,
        "linhas": linhas,
        "markdown": "\n".join(partes),
    }


def executar_analitica_interface(
    pergunta, *, run_id=None, query_id=None, client=None,
    on_progress=None, documental_executor=None
):
    inicio = time.perf_counter()
    run_id = run_id or obs.novo_run_id()
    query_id = query_id or f"q_{uuid.uuid4().hex[:8]}"

    def progresso(valor, texto):
        if on_progress:
            on_progress(valor, texto)

    progresso(0.15, "Interpretando a consulta analítica...")
    interpretacao = interpretar_analitica(
        pergunta, client=client, run_id=run_id, query_id=query_id
    )

    pergunta_analitica = (
        interpretacao.get("pergunta_analitica") or pergunta
    )

    saida = {
        "query": pergunta,
        "run_id": run_id,
        "query_id": query_id,
        "estrategia": "consulta_analitica",
        "routes": ["agregada"],
        "filters": {},
        "plano": {
            "bases": ["agregada"],
            "estrategia": "consulta_analitica",
            "operacao": "executar_plano_analitico",
            "query_id": query_id,
            "plano_analitico": interpretacao.get("plano"),
        },
        "interpretacao_analitica": interpretacao,
        "executado": False,
        "is_refusal": False,
        "necessita_esclarecimento": False,
        "evidences": [],
        "fontes": [],
        "fontes_agregadas": [],
        "fontes_recuperadas": [],
        "fontes_citadas": [],
        "campos": [],
        "registros": [],
        "tokens": dict(interpretacao.get("tokens") or {}),
    }

    def concluir():
        saida["latency_ms"] = round(
            (time.perf_counter() - inicio) * 1000, 2
        )
        progresso(1.0, "Consulta encerrada.")
        return saida

    # A interpretação pode decidir que a pergunta exige documentos.
    # None devolve o controle ao caminho documental existente.
    if interpretacao["tipo"] == "documental":
        return None

    if interpretacao["tipo"] != "plano":
        saida["answer"] = (
            "Não foi possível definir uma operação verificável com os "
            "campos disponíveis. Informe qual dado ou critério deseja consultar."
            if interpretacao.get("tentativas", 0) > 0
            else interpretacao["mensagem"]
        )
        saida["necessita_esclarecimento"] = True
        return concluir()

    # Não executa apenas a parte numérica descartando outro pedido.
    if (
        interpretacao.get("pedido_documental")
        and documental_executor is None
    ):
        saida["answer"] = (
            "A pergunta também contém um pedido documental: "
            + interpretacao["pedido_documental"]
            + ". A integração desse pedido com o novo caminho analítico "
              "ainda não foi concluída. Nenhum cálculo parcial foi executado."
        )
        saida["necessita_esclarecimento"] = True
        return concluir()

    plano = interpretacao["plano"]
    saida["filters"] = {
        tarefa["id"]: tarefa.get("filtros", [])
        for tarefa in plano["tarefas"]
    }

    progresso(0.40, "Calculando sobre os registros do arquivo...")
    with obs.observar_etapa(
        run_id=run_id,
        query_id=query_id,
        stage="consulta_agregada",
        input_data={"tipo": "plano_analitico", "plano": plano},
    ) as evento:
        calculo = executar_fonte(plano)
        evento["output"] = calculo

    origem = calculo["proveniencia"]
    referencia = f"resultado_calculado_{run_id}"

    evidencia = SourceEvidence(
        chunk_id=referencia,
        source_file=Path(origem["arquivo"]).name,
        natureza="agregada",
        base_id="base_agregada",
        sensitivity="publico",
        text=json.dumps({
            "tipo": "resultado_calculado_pelo_executor",
            "aviso": "Não é um chunk recuperado do índice.",
            "pergunta_analitica": pergunta_analitica,
            "plano_executado": calculo["plano"],
            "resultados": calculo["resultados"],
            "comparacoes": calculo.get("comparacoes", []),
            "proveniencia": origem,
            "orientacao": (
                "Responda ao pedido original no formato solicitado. "
                "Contar registros não é somar quantidades físicas. "
                "Diferenca significa esquerda menos direita. "
                "Não acrescente valores ou conclusões não sustentados."
            ),
        }, ensure_ascii=False, indent=2),
        metadata={
            "tipo_evidencia": "resultado_calculado",
            "recuperado_do_indice": False,
            "arquivo": origem["arquivo"],
            "sha256": origem["sha256"],
            "run_id_calculo": run_id,
        },
    )

    saida.update({
        "executado": True,
        "calculo_analitico": calculo,
        "proveniencia_calculo": origem,
        "fontes": [origem["arquivo"]],
        "fontes_agregadas": [origem["arquivo"]],
        "referencias": [referencia],
        "evidences": [{
            "chunk_id": referencia,
            "trecho": evidencia.text,
            "fonte": evidencia.source_file,
            "natureza": "agregada",
            "base": "base_agregada",
            "tipo_evidencia": "resultado_calculado",
            "recuperado_do_indice": False,
        }],
    })

    tabelas = []
    for resultado in calculo["resultados"]:
        if resultado.get("agrupar_por"):
            tabelas.append(renderizar_agrupamento(resultado))
        elif resultado["operacao"] == "listar":
            tabelas.append(_tabela_listagem(resultado))

    # Se houver somente resultados tabulares, usa diretamente os dados.
    somente_tabelas = (
        len(tabelas) == len(calculo["resultados"])
        and not calculo.get("comparacoes")
    )

    if somente_tabelas:
        with obs.observar_etapa(
            run_id=run_id,
            query_id=query_id,
            stage="geracao",
            input_data={"tipo": "apresentacao_deterministica"},
        ) as evento:
            saida["answer"] = "\n\n".join(
                mascarar_dados_pessoais(tabela["markdown"])
                + f"\n\n[Fonte: {referencia}]"
                for tabela in tabelas
            )
            evento["output"] = {
                "formato": "tabela",
                "tabelas": len(tabelas),
                "chamada_ao_modelo": False,
            }
        saida["fontes_citadas"] = [origem["arquivo"]]
        saida["generation_available"] = False
    else:
        progresso(0.70, "Preparando a resposta com os resultados calculados...")
        resposta = gerar_resposta(
            RetrievalResult(
                query=(
                    pergunta_analitica
                ),
                query_id=query_id,
                routes=["agregada"],
                evidences=[evidencia],
            ),
            client=client,
            run_id=run_id,
        )
        saida["answer"] = resposta.answer
        saida["generation_available"] = resposta.stage == "geracao"
        saida["confidence_level"] = resposta.confidence_level
        saida["modelo"] = resposta.modelo
        saida["etapa_final"] = resposta.stage
        if resposta.sources_used:
            saida["fontes_citadas"] = [origem["arquivo"]]
        for chave, atributo in (
            ("prompt", "prompt"),
            ("completion", "completion"),
            ("total", "total"),
        ):
            saida["tokens"][chave] = (
                saida["tokens"].get(chave, 0)
                + getattr(resposta.tokens, atributo, 0)
            )

    # A resposta mostra todas as tabelas; o componente da tela recebe a primeira.
    saida["tabelas_analiticas"] = tabelas
    if tabelas:
        primeira = tabelas[0]
        saida["campos"] = primeira["colunas"]
        saida["registros"] = [
            dict(zip(primeira["colunas"], linha))
            for linha in primeira["linhas"]
        ]

    if interpretacao.get("pedido_documental"):
        from app.analytical_combined import combinar_resultados

        progresso(0.85, "Consultando a parte documental...")
        documental = documental_executor(
            interpretacao["pedido_documental"]
        )
        saida.update(combinar_resultados(
            saida, documental, interpretacao["pedido_documental"]
        ))

    return concluir()
