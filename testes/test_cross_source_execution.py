import csv
import json

from src.router import planejar_consulta
from src.query_executor import executar_plano

ID = "42498600000171-1-000757/2026"
M01 = (
    "Com base no PE 038/26/2026, informe quantos itens foram homologados, "
    "fracassados e desertos, calcule o valor total homologado e verifique "
    "se existe alguma informação relacionada a essa contratação nas demais "
    "naturezas de evidência disponíveis no corpus."
)


def test_planeja_m01():
    plano = planejar_consulta(
        M01,
        analise={
            "query_id": "q_m01",
            "routes": ["agregada"],
            "filters": {},
            "is_refusal": False,
        },
    )
    assert plano["operacao"] == "resumir_itens_vinculos"
    assert plano["estrategia"] == "consulta_agregada"
    assert plano["filtros"]["id_contratacao_pncp"] == ID


def test_calculo_e_vinculos_independentes_de_top_k(tmp_path):
    itens = tmp_path / "itens.csv"
    with itens.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[
            "id_contratacao_pncp", "numero_item", "situacao_item",
            "valor_total_homologado", "url_fonte",
        ])
        escritor.writeheader()
        escritor.writerow({
            "id_contratacao_pncp": ID,
            "numero_item": "1",
            "situacao_item": "Homologado",
            "valor_total_homologado": "10.25",
            "url_fonte": "",
        })

    chunks = tmp_path / "chunks.json"
    chunks.write_text(json.dumps([
        {
            "chunk_id": "ata",
            "text": f"Ata relacionada a {ID}.",
            "metadata": {
                "natureza": "conversacional",
                "source_file": "ata.txt",
            },
        },
        {
            "chunk_id": "lei",
            "text": "Lei 14.133/2021: regras gerais.",
            "metadata": {
                "natureza": "normativa",
                "source_file": "lei.html",
            },
        },
    ]), encoding="utf-8")

    plano = {
        "bases": ["agregada"],
        "estrategia": "consulta_agregada",
        "operacao": "resumir_itens_vinculos",
        "filtros": {"id_contratacao_pncp": ID},
        "arquivo": str(itens),
        "arquivo_chunks": str(chunks),
        "query_id": "q_m01",
    }

    for limite in (1, 3, 5):
        resultado = executar_plano(M01, plano, top_k=limite)
        assert resultado["itens_total"] == 1
        assert resultado["valor_total_homologado"] == "10.25"
        assert resultado["total_chunks_verificados"] == 2
        assert resultado["total_vinculos_complementares"] == 1
        assert "ata.txt" in resultado["fontes"]
        assert "lei.html" not in resultado["fontes"]
        assert resultado["verificacao_vinculos"]["correspondencias"]["normativa"] == []
