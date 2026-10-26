"""Demonstração offline com planos explícitos e cálculos reais."""

import os
from pathlib import Path

from src import obs
from src.document_scope import normalizar
from src.query_executor import executar_plano


PERGUNTAS = {
    "P02": (
        "No PE 038/26/2026, quantos itens foram homologados, "
        "fracassados e desertos e qual foi a soma dos valores homologados?"
    ),
    "P07": (
        "Quantos itens constam no Plano de Contratações Anual "
        "do Estado do Rio de Janeiro para 2026 "
        "e qual é o valor total estimado informado?"
    ),
    "M01": (
        "Resuma o PE 038/26/2026 e verifique os vínculos "
        "nas demais naturezas do corpus."
    ),
}


def executar_demo(
    pergunta, *, top_k=3, fetch_k=50,
    criterio_tecnologia=None, run_id=None,
):
    run_id = run_id or obs.novo_run_id()
    query_id = "q_demo_" + obs.novo_run_id()
    caso = next(
        (nome for nome, texto in PERGUNTAS.items()
         if normalizar(texto) == normalizar(pergunta)),
        None,
    )
    identificacao = {
        "modo_demonstracao": "offline",
        "roteamento_demonstracao": "plano local predefinido",
        "commit_demonstracao": os.getenv("RAG_DEMO_COMMIT", ""),
        "versao_artefatos": "v3; M01 usa corpus corrigido de 2172 chunks",
    }

    if caso is None:
        mensagem = (
            "Demonstração offline: utilize uma das perguntas P02, P07 "
            "ou M01 apresentadas nos exemplos. Outras consultas exigem "
            "o fluxo normal e a disponibilidade do servidor."
        )
        return {
            **identificacao,
            "query": pergunta,
            "query_id": query_id,
            "run_id": run_id,
            "executado": False,
            "mensagem": mensagem,
            "plano": {
                "bases": [],
                "estrategia": "esclarecimento",
                "necessita_esclarecimento": True,
                "pergunta_esclarecimento": mensagem,
            },
        }

    pacote = Path(os.environ["RAG_DEMO_PACOTE"])
    chunks = Path(os.environ["RAG_DEMO_CHUNKS"])
    operacao = {
        "P02": "resumir_itens",
        "P07": "resumir_pca",
        "M01": "resumir_itens_vinculos",
    }[caso]
    arquivo = pacote / "data/raw/v3/agregada" / (
        "pca_2026_estado_rj.csv" if caso == "P07"
        else "itens_pe_038_26_2026.csv"
    )
    if not arquivo.is_file() or (caso == "M01" and not chunks.is_file()):
        raise FileNotFoundError("Arquivos da demonstração não encontrados.")

    plano = {
        "bases": ["agregada"],
        "estrategia": "consulta_agregada",
        "operacao": operacao,
        "filtros": {} if caso == "P07" else {
            "id_contratacao_pncp": "42498600000171-1-000757/2026"
        },
        "arquivo": str(arquivo),
        "arquivo_chunks": str(chunks),
        "query_id": query_id,
    }
    if caso == "P07":
        plano["recorte_fonte"] = {
            "documento": "PCA", "uf": "RJ", "ano": 2026,
            "observacao": "Recorte associado à fonte; cálculo de todas as linhas.",
        }
    else:
        plano["processo_informado"] = "PE 038/26/2026"

    with obs.observar_etapa(
        run_id=run_id, query_id=query_id,
        stage="roteamento",
        input_data={"caso": caso, "modo": "offline"},
    ) as evento:
        evento["output"] = {
            "bases": ["agregada"],
            "operacao": operacao,
            "filtros": plano["filtros"],
            "roteador_llm_executado": False,
            **identificacao,
        }

    resultado = executar_plano(
        pergunta, plano, top_k=top_k, fetch_k=fetch_k,
        client=object(), run_id=run_id,
    )
    return {
        **resultado, **identificacao,
        "plano": plano, "executado": True,
    }
