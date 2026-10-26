from copy import deepcopy
import json

from src.retrieval_lexical import (
    buscar_contexto,
    texto_contexto,
    tokenizar_contexto,
)


def natureza(chunk):
    return chunk["metadata"]["natureza"]


def test_normaliza_acentos_e_variacoes():
    assert tokenizar_contexto("Vidraça e vidraçaria") == [
        "vidrac", "vidrac"
    ]
    assert tokenizar_contexto("Elevador e elevadores") == [
        "elevador", "elevador"
    ]


def test_busca_no_objeto_sem_usar_metadados_do_json():
    chunk = {
        "text": json.dumps({
            "objetoCompra": "Manutenção de vidraçaria.",
            "nomeOrgao": "Hospital de Elevadores",
        }),
        "metadata": {"natureza": "estruturada"},
    }

    assert texto_contexto(chunk, natureza) == (
        "Manutenção de vidraçaria."
    )


def test_prioriza_vidracaria_sem_mutacao():
    chunks = {
        "a": {
            "text": json.dumps({
                "objetoCompra": "Serviços de vidraçaria."
            }),
            "metadata": {"natureza": "estruturada"},
        },
        "b": {
            "text": json.dumps({
                "objetoCompra": "Reparo de galerias pluviais."
            }),
            "metadata": {"natureza": "estruturada"},
        },
        "c": {
            "text": json.dumps({
                "objetoCompra": "Aquisição de cadeiras."
            }),
            "metadata": {"natureza": "estruturada"},
        },
    }
    original = deepcopy(chunks)

    resultado = buscar_contexto(
        "Existe contratação para reparo de vidraça?",
        [{"chunk_id": identificador} for identificador in chunks],
        chunks,
        natureza,
        fetch_k=1,
    )

    assert resultado[0]["chunk_id"] == "a"
    assert resultado[0]["bm25_score"] > 0
    assert chunks == original


def test_nao_inclui_candidato_fora_do_recorte():
    chunks = {
        "permitido": {
            "text": "Aquisição de cadeiras.",
            "metadata": {"natureza": "estruturada"},
        },
        "fora": {
            "text": "Serviços de vidraçaria.",
            "metadata": {"natureza": "estruturada"},
        },
    }

    resultado = buscar_contexto(
        "vidraça",
        [{"chunk_id": "permitido"}],
        chunks,
        natureza,
    )

    assert resultado == []


def test_lista_vazia_e_pergunta_sem_tokens():
    assert buscar_contexto("vidraça", [], {}, natureza) == []
    assert buscar_contexto(
        "a e o",
        [{"chunk_id": "1"}],
        {"1": {
            "text": "Pregão.",
            "metadata": {"natureza": "normativa"},
        }},
        natureza,
    ) == []
