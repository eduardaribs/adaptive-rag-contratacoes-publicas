"""Cálculos determinísticos sobre CSVs completos do corpus."""

import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


def ler_csv(caminho, separador, campos_obrigatorios):
    caminho = Path(caminho)

    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=separador)
        campos = set(leitor.fieldnames or [])
        faltantes = set(campos_obrigatorios) - campos
        if faltantes:
            raise ValueError(f"Colunas ausentes: {sorted(faltantes)}")

        registros = []
        for numero, registro in enumerate(leitor, start=2):
            if None in registro or any(v is None for v in registro.values()):
                raise ValueError(f"Linha CSV malformada: {numero}")
            registros.append(registro)

    return registros


def decimal_csv(valor, *, formato):
    texto = str(valor or "").strip()
    if not texto:
        return None

    if formato == "br":
        texto = texto.replace(".", "").replace(",", ".")
    elif formato != "decimal":
        raise ValueError("Formato numérico inválido.")

    try:
        numero = Decimal(texto)
    except InvalidOperation as erro:
        raise ValueError(f"Valor numérico inválido: {valor!r}") from erro

    if not numero.is_finite():
        raise ValueError(f"Valor não finito: {valor!r}")

    return numero


def resumir_itens(caminho, *, id_contratacao):
    registros = ler_csv(
        caminho, ",",
        {
            "id_contratacao_pncp", "numero_item",
            "situacao_item", "valor_total_homologado", "url_fonte",
        },
    )

    selecionados = [
        r for r in registros
        if r["id_contratacao_pncp"].strip() == id_contratacao
    ]

    numeros = [r["numero_item"].strip() for r in selecionados]
    if any(not n for n in numeros) or len(numeros) != len(set(numeros)):
        raise ValueError("Número de item ausente ou duplicado na contratação.")

    situacoes = Counter()
    soma = Decimal("0")
    ausentes = 0

    for registro in selecionados:
        situacao = registro["situacao_item"].strip().casefold()
        if situacao not in {"homologado", "fracassado", "deserto"}:
            raise ValueError(f"Situação não suportada: {situacao!r}")
        situacoes[situacao] += 1

        if situacao == "homologado":
            valor = decimal_csv(
                registro["valor_total_homologado"],
                formato="decimal",
            )
            if valor is None:
                ausentes += 1
            else:
                soma += valor

    return {
        "estrategia": "consulta_agregada",
        "operacao": "resumir_itens",
        "filtros_aplicados": {"id_contratacao_pncp": id_contratacao},
        "total_base": len(registros),
        "itens_total": len(selecionados),
        "homologados": situacoes["homologado"],
        "fracassados": situacoes["fracassado"],
        "desertos": situacoes["deserto"],
        "valor_total_homologado": str(soma),
        "homologados_sem_valor": ausentes,
        "soma_completa": ausentes == 0,
        "fontes": [str(Path(caminho))],
        "referencias": sorted({
            r["url_fonte"].strip()
            for r in selecionados if r["url_fonte"].strip()
        }),
        "observacao": (
            "Soma dos valores informados dos itens homologados "
            "da contratação selecionada no arquivo carregado."
        ),
    }


def resumir_pca(caminho):
    registros = ler_csv(
        caminho, ";",
        {"UASG", "Id do item no PCA", "Valor Total Estimado (R$)"},
    )

    soma = Decimal("0")
    ausentes = 0

    for registro in registros:
        valor = decimal_csv(
            registro["Valor Total Estimado (R$)"],
            formato="br",
        )
        if valor is None:
            ausentes += 1
        else:
            soma += valor

    return {
        "estrategia": "consulta_agregada",
        "operacao": "resumir_pca",
        "filtros_aplicados": {},
        "total_itens": len(registros),
        "valor_total_estimado": str(soma),
        "itens_sem_valor": ausentes,
        "soma_completa": ausentes == 0,
        "fontes": [str(Path(caminho))],
        "observacao": (
            "Contagem de linhas de dados e soma do campo "
            "'Valor Total Estimado (R$)' de todo o arquivo carregado. "
            "O recorte de ano e UF deve ser confirmado pela origem do arquivo."
        ),
    }


def executar_agregada(plano):
    """Executa somente as operações e filtros agregados suportados."""
    if plano.get("bases") != ["agregada"]:
        raise ValueError("A consulta agregada exige somente a base agregada.")

    operacao = plano.get("operacao")
    filtros = dict(plano.get("filtros") or {})
    raiz_projeto = Path(__file__).resolve().parents[1]

    if operacao == "resumir_itens_vinculos":
        import json
        from src.cross_source import verificar_vinculos

        plano_itens = {
            **plano,
            "operacao": "resumir_itens",
        }
        resumo = executar_agregada(plano_itens)

        caminho_chunks = plano.get("arquivo_chunks")
        if caminho_chunks is None:
            caminho_chunks = raiz_projeto / "data/processed/chunks_teste.json"

        caminho_chunks = Path(caminho_chunks)
        chunks = json.loads(caminho_chunks.read_text(encoding="utf-8"))
        if not isinstance(chunks, list):
            raise ValueError("O arquivo de chunks deve conter uma lista.")

        verificacao = verificar_vinculos(
            chunks,
            id_contratacao=filtros["id_contratacao_pncp"].strip(),
        )

        fontes_complementares = {
            evidencia["fonte"]
            for natureza, evidencias in verificacao["correspondencias"].items()
            if natureza != "agregada"
            for evidencia in evidencias
            if evidencia.get("fonte")
        }

        return {
            **resumo,
            "operacao": "resumir_itens_vinculos",
            "verificacao_vinculos": verificacao,
            "total_chunks_verificados": verificacao["total_chunks_verificados"],
            "total_vinculos_complementares": sum(
                len(evidencias)
                for natureza, evidencias
                in verificacao["correspondencias"].items()
                if natureza != "agregada"
            ),
            "fonte_corpus_verificado": str(caminho_chunks),
            "fontes": sorted(set(resumo["fontes"]) | fontes_complementares),
        }

    if operacao == "resumir_itens":
        if set(filtros) != {"id_contratacao_pncp"}:
            raise ValueError(
                "resumir_itens exige apenas id_contratacao_pncp."
            )

        identificador = filtros["id_contratacao_pncp"]
        if not isinstance(identificador, str) or not identificador.strip():
            raise ValueError("ID da contratação inválido.")

        caminho = plano.get("arquivo")
        if caminho is None:
            caminho = raiz_projeto / (
                "data/raw/v3/agregada/itens_pe_038_26_2026.csv"
            )

        return resumir_itens(
            caminho,
            id_contratacao=identificador.strip(),
        )

    if operacao == "resumir_pca":
        if filtros:
            raise ValueError(
                "O resumo do PCA ainda não aceita filtros. "
                "Ele calcula sobre todo o arquivo."
            )

        caminho = plano.get("arquivo")
        if caminho is None:
            caminho = raiz_projeto / (
                "data/raw/v3/agregada/pca_2026_estado_rj.csv"
            )

        return resumir_pca(caminho)

    raise ValueError("Operação agregada não suportada.")
