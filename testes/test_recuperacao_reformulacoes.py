"""Regressões reconstruídas após a recuperação do ambiente."""

from copy import deepcopy
from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from src.analytical_executor import executar_analitico
from src.analytical_plan import PlanoAnalitico
from src.analytical_transport import decodificar_interpretacao
from src.document_scope import escopar_documento
from src.retrieval_lexical import buscar_contexto, tokenizar_contexto


def registros():
    return [
        {"numero_item": "1", "fornecedor": "A",
         "situacao_item": "homologado", "valor_total_homologado": "0.1"},
        {"numero_item": "2", "fornecedor": "A",
         "situacao_item": "homologado", "valor_total_homologado": "0.2"},
        {"numero_item": "3", "fornecedor": "B",
         "situacao_item": "homologado", "valor_total_homologado": "0.3"},
        {"numero_item": "4", "fornecedor": "C",
         "situacao_item": "fracassado", "valor_total_homologado": None},
    ]


def lista(**extras):
    return {
        "id": "lista", "operacao": "listar",
        "campos": ["fornecedor"], "distintos": True,
        "filtros": [{
            "campo": "situacao_item", "operador": "igual",
            "valor": "homologado",
        }],
        **extras,
    }


def calcular(tarefas):
    return executar_analitico(
        {"fonte": "itens_pe", "tarefas": tarefas}, registros()
    )["resultados"]


def test_distintos_antes_do_limite_sem_alterar_contagem_e_soma():
    resultados = calcular([
        lista(limite=1),
        {"id": "contagem", "operacao": "contar",
         "filtros": lista()["filtros"]},
        {"id": "soma", "operacao": "somar",
         "campo": "valor_total_homologado",
         "filtros": lista()["filtros"]},
    ])
    assert resultados[0]["registros"] == [{"fornecedor": "A"}]
    assert resultados[0]["total_registros"] == 3
    assert resultados[0]["total_resultados"] == 2
    assert resultados[0]["truncado"] is True
    assert resultados[1]["valor"] == 3
    assert Decimal(resultados[2]["valor"]) == Decimal("0.6")


def test_itens_diferentes_do_mesmo_fornecedor_sao_preservados():
    resultado = calcular([lista(campos=["numero_item", "fornecedor"])])[0]
    assert resultado["total_resultados"] == 3
    assert {r["numero_item"] for r in resultado["registros"]} == {"1", "2", "3"}


def test_listagem_comum_preserva_repeticoes():
    resultado = calcular([lista(distintos=False)])[0]
    assert [r["fornecedor"] for r in resultado["registros"]] == ["A", "A", "B"]


def test_listagem_distinta_nao_modifica_entrada():
    entrada = registros()
    antes = deepcopy(entrada)
    executar_analitico(
        {"fonte": "itens_pe", "tarefas": [lista()]}, entrada
    )
    assert entrada == antes


def test_distintos_nao_ordena_por_campo_oculto():
    with pytest.raises(ValidationError):
        PlanoAnalitico.model_validate({
            "fonte": "itens_pe",
            "tarefas": [lista(ordenar_por="valor_total_homologado")],
        })


def proposta(**extras):
    return {
        "tipo": "plano", "mensagem": "", "pedido_documental": None,
        "plano": {
            "fonte": "itens_pe",
            "tarefas": [{
                "id": "x", "operacao": "listar",
                "campos": ["fornecedor"], **extras,
            }],
        },
    }


def test_modelo_precisa_decidir_sobre_distintos():
    with pytest.raises(ValidationError):
        decodificar_interpretacao(json.dumps(proposta()))


@pytest.mark.parametrize("distintos", [True, False])
def test_decisao_explicita_e_preservada(distintos):
    resultado = decodificar_interpretacao(json.dumps(
        proposta(distintos=distintos)
    ))
    assert resultado["plano"]["tarefas"][0]["distintos"] is distintos


@pytest.mark.parametrize("pergunta", [
    "No PE 038/26/2026, quais itens foram homologados?",
    "Relacione os itens homologados do PE 038/26/2026.",
    "Quais fornecedores tiveram itens homologados no PE 038/26/2026?",
    "Explique a homologação no PE 038/26/2026.",
    "Quais categorias aparecem no PCA RJ 2026?",
])
def test_candidatura_nao_depende_de_verbo_especifico(monkeypatch, pergunta):
    from app import analytical_dispatch as modulo
    monkeypatch.setenv("RAG_ANALYTICAL_ENABLED", "true")
    monkeypatch.setenv("RAG_DEMO_OFFLINE", "false")
    assert modulo.deve_usar_analitica(pergunta, {})


@pytest.mark.parametrize("tentativas", [0, 1])
def test_mensagem_do_modelo_nao_vira_resposta_factual(
    monkeypatch, tmp_path, tentativas
):
    from app import analytical_adapter as modulo
    monkeypatch.setattr(modulo.obs, "PASTA_LOGS", tmp_path)
    monkeypatch.setattr(
        modulo, "interpretar_analitica",
        lambda *a, **k: {
            "tipo": "esclarecimento",
            "mensagem": "AFIRMACAO_SEM_SUPORTE",
            "plano": None, "tentativas": tentativas,
        },
    )
    resultado = modulo.executar_analitica_interface("Pergunta")
    assert resultado["necessita_esclarecimento"] is True
    assert resultado["executado"] is False
    if tentativas:
        assert "AFIRMACAO_SEM_SUPORTE" not in resultado["answer"]
    else:
        assert resultado["answer"] == "AFIRMACAO_SEM_SUPORTE"


def test_decisao_documental_devolve_controle(monkeypatch):
    from app import analytical_adapter as modulo
    monkeypatch.setattr(
        modulo, "interpretar_analitica",
        lambda *a, **k: {
            "tipo": "documental", "mensagem": "Consultar documentos.",
            "plano": None,
        },
    )
    assert modulo.executar_analitica_interface("Explique") is None


def test_esclarecimento_do_modelo_preserva_caminho_documental(
    monkeypatch, tmp_path
):
    from app import analytical_dispatch as modulo
    from app import analytical_adapter
    from src import obs
    monkeypatch.setenv("RAG_ANALYTICAL_ENABLED", "true")
    monkeypatch.setenv("RAG_DEMO_OFFLINE", "false")
    monkeypatch.setattr(obs, "PASTA_LOGS", tmp_path)
    monkeypatch.setattr(
        analytical_adapter, "executar_analitica_interface",
        lambda *a, **k: {
            "necessita_esclarecimento": True,
            "interpretacao_analitica": {
                "tipo": "esclarecimento", "tentativas": 1,
            },
        },
    )
    resultado = modulo.tentar_analitica(
        "Explique homologação no PE 038/26/2026.",
        {"estrategia": "recuperacao_hibrida",
         "query_id": "q_recuperacao",
         "routes": ["normativa", "conversacional"], "executado": True},
        run_id="run_recuperacao",
    )
    assert resultado is None


@pytest.mark.parametrize("referencia", [
    "PE 038/26/2026", "PE 123/2026",
    "PE nº 038/26/2026", "PE n.º 038/26/2026",
])
def test_identificador_nao_e_uf(referencia):
    from src import router
    assert router._extrair_ufs_explicitas(
        "Explique a homologação no " + referencia
    ) == set()


@pytest.mark.parametrize("uf", ["PE", "RJ"])
def test_uf_fora_do_identificador_e_preservada(uf):
    from src import router
    assert router._extrair_ufs_explicitas(
        "Itens do PE 038/26/2026 de órgãos em " + uf
    ) == {uf}


def test_identificador_nao_cria_ano_ou_modalidade():
    from src import router
    resultado = router._validar_filtros_contra_pergunta(
        "Explique a homologação no PE 038/26/2026.",
        {"uf": "PE", "ano": 2026, "modalidade": "PE 038/26/2026"},
    )
    assert all(resultado[c] is None for c in ("uf", "ano", "modalidade"))


def chunk(fonte, natureza, texto):
    return {
        "text": texto,
        "metadata": {"source_file": fonte, "natureza": natureza},
    }


def test_escopo_preserva_norma_e_exclui_outro_pregao():
    chunks = {
        "norma": chunk("lei.html", "normativa", "Regra geral."),
        "outro": chunk("ata.pdf", "conversacional", "PE 91.051/2026."),
        "dados": chunk("itens_pe_038_26_2026.csv", "agregada", "Dados."),
        "edital": chunk("edital.pdf", "conversacional", "PE 038/26/2026."),
        "pagina": chunk("edital.pdf", "conversacional", "Outra página."),
    }
    resultado = escopar_documento(
        "Explique no PE 038/26/2026.", chunks,
        lambda item: item["metadata"]["natureza"],
    )
    assert resultado["ids"] == {"norma", "dados", "edital", "pagina"}


def test_fonte_com_dois_pregoes_nao_e_associada_automaticamente():
    chunks = {
        "ambiguo": chunk(
            "compilacao.pdf", "conversacional",
            "PE 038/26/2026 e PE 039/26/2026.",
        ),
        "norma": chunk("lei.html", "normativa", "Regra geral."),
    }
    resultado = escopar_documento(
        "PE 038/26/2026", chunks,
        lambda item: item["metadata"]["natureza"],
    )
    assert resultado["ids"] == {"norma"}


def test_ausencia_de_identificador_preserva_fluxo():
    assert escopar_documento(
        "Explique homologação.", {},
        lambda item: item["metadata"]["natureza"],
    ) is None


@pytest.mark.parametrize("formas", [
    ["homologação", "homologar", "homologado"],
    ["revogação", "revogar"],
    ["licitação", "licitar"],
])
def test_normalizacao_preserva_acentos_ate_o_stemming(formas):
    tokens = [tokenizar_contexto(forma) for forma in formas]
    assert tokens[0]
    assert all(item == tokens[0] for item in tokens)


def test_busca_recupera_verbo_a_partir_do_substantivo():
    chunks = {
        "decisao": chunk("lei.html", "normativa",
                        "A autoridade superior poderá homologar a licitação."),
        "edital": chunk("lei.html", "normativa", "Divulgação do edital."),
        "prazo": chunk("lei.html", "normativa", "Contagem de dias úteis."),
        "garantia": chunk("lei.html", "normativa", "Prestação de garantia."),
    }
    resultados = buscar_contexto(
        "homologação",
        [{"chunk_id": identificador} for identificador in chunks],
        chunks,
        lambda item: item["metadata"]["natureza"],
    )
    assert resultados[0]["chunk_id"] == "decisao"
