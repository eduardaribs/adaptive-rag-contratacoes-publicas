
from copy import deepcopy
import json

from app.interface_results import (
    preparar_estruturado,
    preparar_combinado,
    mudar_pagina,
    tabela_consulta,
    feedback_da_consulta,
)


def criar_resultado():
    estruturada = {
        "estrategia": "consulta_estruturada",
        "operacao": "listar",
        "total_base": 10,
        "total": 3,
        "filtros_aplicados": {"ano_compra": 2026},
        "campos": ["objeto"],
        "registros": [{"objeto": "A"}, {"objeto": "B"}],
        "referencias": [
            {"id_pncp": "1", "fonte": "contratacoes.json"},
            {"id_pncp": "2", "fonte": "contratacoes.json"},
        ],
        "fontes": ["contratacoes.json"],
        "pagina": 1,
        "tamanho_pagina": 2,
        "total_paginas": 2,
    }
    consulta = {
        "estruturada": estruturada,
        "routes": ["estruturada", "normativa"],
        "plano": {
            "bases": ["estruturada", "normativa"],
            "estrategia": "combinada",
            "operacao": "listar",
            "filtros": {"ano_compra": 2026},
            "campos": ["objeto"],
            "pagina": 1,
            "tamanho_pagina": 2,
            "query_id": "q_original",
        },
    }
    documental = {
        "query": "Liste as contratações e explique a regra.",
        "query_id": "q_original",
        "run_id": "run_original",
        "executado": True,
        "answer": "Explicação documental. [Fonte: lei.html]",
        "fontes": ["lei.html"],
        "fontes_recuperadas": ["lei.html"],
        "fontes_citadas": ["lei.html"],
        "evidences": [{
            "chunk_id": "lei_chunk_1",
            "fonte": "lei.html",
            "trecho": "Trecho documental.",
        }],
        "tokens": {"total": 20},
        "latency_ms": 100,
        "top_k": 1,
        "fetch_k": 50,
    }
    return consulta, documental


def test_fontes_estruturadas_preenchidas():
    consulta, _ = criar_resultado()
    resultado = preparar_estruturado(consulta["estruturada"])

    assert resultado["fontes_estruturadas"] == ["contratacoes.json"]


def test_combinada_preserva_calculo_campos_e_fontes():
    consulta, documental = criar_resultado()
    original = deepcopy(consulta)

    resultado = preparar_combinado(consulta, documental)

    assert resultado["estrategia"] == "combinada"
    assert resultado["total"] == 3
    assert resultado["total_base"] == 10
    assert resultado["filters"] == {"ano_compra": 2026}
    assert tabela_consulta(resultado) == {
        "headers": ["objeto"],
        "data": [["A"], ["B"]],
    }
    assert set(resultado["fontes"]) == {
        "contratacoes.json", "lei.html"
    }
    assert resultado["fontes_citadas"] == ["lei.html"]
    assert "Explicação documental." in resultado["answer"]
    assert consulta == original


def test_paginacao_combinada_nao_repete_busca_documental():
    consulta, documental = criar_resultado()
    resultado = preparar_combinado(consulta, documental)
    original = deepcopy(resultado)
    chamadas = []

    def executor(pergunta, plano, run_id):
        chamadas.append(deepcopy(plano))
        assert plano["estrategia"] == "consulta_estruturada"
        assert plano["bases"] == ["estruturada"]
        assert plano["filtros"] == {"ano_compra": 2026}
        assert plano["pagina"] == 2

        return {
            **deepcopy(consulta["estruturada"]),
            "query": pergunta,
            "query_id": "q_original",
            "run_id": "run_pagina",
            "pagina": 2,
            "registros": [{"objeto": "C"}],
            "referencias": [{
                "id_pncp": "3",
                "fonte": "contratacoes.json",
            }],
        }

    nova = mudar_pagina(resultado, 1, executor=executor)

    assert len(chamadas) == 1
    assert nova["pagina"] == 2
    assert nova["total"] == 3
    assert nova["registros"] == [{"objeto": "C"}]
    assert nova["estrategia"] == "combinada"
    assert nova["resposta_documental"] == documental["answer"]
    assert nova["evidences"] == resultado["evidences"]
    assert nova["documental_run_id"] == "run_original"
    assert nova["paginacao_run_id"] == "run_pagina"
    assert nova["query_id"] == "q_original"
    assert resultado == original


def test_feedback_combinado_persiste_contexto_e_ambas_fontes(
    tmp_path, monkeypatch
):
    caminho = tmp_path / "feedback.jsonl"
    monkeypatch.setenv("FEEDBACK_PATH", str(caminho))

    consulta, documental = criar_resultado()
    resultado = preparar_combinado(consulta, documental)

    mensagem = feedback_da_consulta(
        resultado, "util", "Validação do vínculo."
    )

    assert "salvo" in mensagem.lower()
    registros = [
        json.loads(linha)
        for linha in caminho.read_text(encoding="utf-8").splitlines()
    ]
    assert len(registros) == 1
    registro = registros[0]

    assert registro["pergunta"] == documental["query"]
    assert registro["query_id"] == "q_original"
    assert registro["run_id"] == "run_original"
    assert set(registro["fontes"]) == {
        "contratacoes.json", "lei.html"
    }
