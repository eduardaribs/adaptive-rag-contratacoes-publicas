"""Consulta determinística aos registros normalizados do PNCP."""

import json
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path

CAMINHO_BASE = Path("data/processed/base_estruturada_normalizada.json")

CAMPOS = {
    "id_pncp", "orgao", "municipio", "uf", "objeto",
    "modalidade", "ano_compra", "data_publicacao",
    "valor_estimado", "valor_homologado", "fornecedor",
    "fonte_original",
}

FILTROS = {
    "uf", "municipio", "orgao", "modalidade", "fornecedor",
    "ano_compra", "objeto_termos",
    "valor_minimo", "valor_maximo",
}

CAMPOS_PADRAO = ["id_pncp", "orgao", "objeto"]


def normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return " ".join(
        "".join(c for c in texto if not unicodedata.combining(c))
        .casefold().split()
    )


def converter_numero(valor):
    """Aceita números JSON e textos brasileiros; ausência não vira zero."""
    if valor is None or isinstance(valor, bool):
        return None

    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        numero = Decimal(texto)
        return numero if numero.is_finite() else None
    except InvalidOperation:
        return None


def carregar_base(caminho=CAMINHO_BASE):
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(f"Base normalizada ausente: {caminho}")

    base = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(base, list):
        raise ValueError("A base precisa ser uma lista de registros.")

    validar_base(base)
    return base


def validar_base(base):
    ids = []
    for registro in base:
        if not isinstance(registro, dict):
            raise ValueError("Registro inválido na base.")

        identificador = registro.get("id_pncp")
        if not isinstance(identificador, str) or not identificador.strip():
            raise ValueError("Registro sem ID PNCP válido.")
        ids.append(identificador)

    if len(ids) != len(set(ids)):
        raise ValueError("A base possui IDs PNCP duplicados.")



def _validar_data_filtro(valor, campo):
    from datetime import date
    import re

    if valor is None:
        return None

    if not isinstance(valor, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}", valor
    ):
        raise ValueError(f"{campo} deve usar YYYY-MM-DD.")

    try:
        return date.fromisoformat(valor)
    except ValueError as erro:
        raise ValueError(f"Data inválida: {campo}.") from erro


def _ler_original_pncp(registro):
    original = registro.get("texto_integral")

    if not isinstance(original, str):
        raise ValueError(
            "Filtros de publicação e modalidade_id exigem "
            "texto_integral com o registro original do PNCP."
        )

    try:
        dados = json.loads(original)
    except json.JSONDecodeError as erro:
        raise ValueError("JSON original do PNCP inválido.") from erro

    if not isinstance(dados, dict):
        raise ValueError("O registro original deve ser um objeto JSON.")

    return dados


FILTROS.update({"data_inicial", "data_final", "modalidade_id"})
CAMPOS.add("modalidade_id")


def consultar_registros(
    base,
    operacao="contar",
    filtros=None,
    campos=None,
    pagina=1,
    tamanho_pagina=20,
    campo_valor=None,
    minimo_inclusivo=True,
    maximo_inclusivo=True,
    criterio_objeto=None,
    criterio_tecnologia=None,
):
    """
    Consulta toda a base e pagina apenas a apresentação.

    objeto_termos usa correspondência textual OU no objeto.
    Não é classificação semântica de tecnologia.
    Limites podem ser inclusivos ou estritos.
    """
    validar_base(base)

    if operacao not in {"contar", "listar"}:
        raise ValueError("Operação suportada: contar ou listar.")

    if (
        type(pagina) is not int or pagina < 1
        or type(tamanho_pagina) is not int
        or not 1 <= tamanho_pagina <= 100
    ):
        raise ValueError("Página positiva e tamanho entre 1 e 100.")

    if not isinstance(minimo_inclusivo, bool) or not isinstance(
        maximo_inclusivo, bool
    ):
        raise ValueError("Inclusividade dos limites deve ser booleana.")

    filtros = dict(filtros or {})
    desconhecidos = set(filtros) - FILTROS
    if desconhecidos:
        raise ValueError(
            f"Filtros não suportados: {sorted(desconhecidos)}. "
            "Não serão ignorados silenciosamente."
        )

    campos = list(CAMPOS_PADRAO if campos is None else campos)
    if not campos or set(campos) - CAMPOS:
        raise ValueError("Campos solicitados inválidos ou vazios.")
    campos = list(dict.fromkeys(campos))

    termos = filtros.get("objeto_termos") or []
    if not isinstance(termos, list) or any(
        not isinstance(t, str) or not t.strip() for t in termos
    ):
        raise ValueError("objeto_termos deve ser uma lista de termos.")

    if termos and not criterio_objeto:
        raise ValueError("Informe a descrição do critério usado no objeto.")

    limites = {}
    for nome in ("valor_minimo", "valor_maximo"):
        bruto = filtros.get(nome)
        numero = converter_numero(bruto)
        if bruto is not None and numero is None:
            raise ValueError(f"Limite numérico inválido: {nome}")
        limites[nome] = numero

    minimo = limites["valor_minimo"]
    maximo = limites["valor_maximo"]

    if minimo is not None and maximo is not None and minimo > maximo:
        raise ValueError("Valor mínimo superior ao máximo.")

    tem_limite = minimo is not None or maximo is not None
    if tem_limite and campo_valor not in {
        "valor_estimado", "valor_homologado"
    }:
        raise ValueError(
            "Escolha valor_estimado ou valor_homologado para filtrar."
        )

    ano = filtros.get("ano_compra")
    if ano is not None:
        texto_ano = str(ano)
        if len(texto_ano) != 4 or not texto_ano.isdigit():
            raise ValueError("Ano da compra deve possuir quatro dígitos.")

    data_inicial = _validar_data_filtro(
        filtros.get("data_inicial"), "data_inicial"
    )
    data_final = _validar_data_filtro(
        filtros.get("data_final"), "data_final"
    )

    if data_inicial and data_final and data_inicial > data_final:
        raise ValueError("Data inicial posterior à data final.")

    modalidade_id = filtros.get("modalidade_id")
    if modalidade_id is not None:
        if type(modalidade_id) is not int or modalidade_id <= 0:
            raise ValueError("modalidade_id deve ser inteiro positivo.")

    filtrar_publicacao = data_inicial is not None or data_final is not None
    registros_sem_publicacao = 0
    classificacoes_tic = {}
    resumo_tic = None

    if criterio_tecnologia is not None:
        from src.technology_classifier import (
            VERSAO_CRITERIO,
            classificar_registro,
        )

        if (
            not isinstance(criterio_tecnologia, dict)
            or criterio_tecnologia.get("implementacao") != VERSAO_CRITERIO
        ):
            raise ValueError("Implementação do critério TIC inválida.")

        if not criterio_tecnologia.get("descricao"):
            raise ValueError("Descrição do critério TIC ausente.")

        tipo_tic = criterio_tecnologia.get("tipo", "todos")
        if tipo_tic not in {
            "todos", "bem_proposto", "servico_proposto"
        }:
            raise ValueError("Tipo de TIC inválido.")

        if termos:
            raise ValueError(
                "Não combine classificação contextual "
                "com objeto_termos na mesma consulta."
            )

        criterio_objeto = criterio_tecnologia["descricao"]
        resumo_tic = {
            "implementacao": VERSAO_CRITERIO,
            "tipo_solicitado": tipo_tic,
            "registros_no_recorte": 0,
            "tic_proposto": 0,
            "revisao": 0,
            "sem_indicio": 0,
            "tipo_indeterminado": 0,
            "classificacao_humana_validada": False,
        }

    selecionados = []

    for registro in base:
        if filtrar_publicacao or modalidade_id is not None:
            original = _ler_original_pncp(registro)

            if modalidade_id is not None:
                if original.get("modalidadeId") != modalidade_id:
                    continue

            if filtrar_publicacao:
                publicacao = original.get("dataPublicacaoPncp")

                if publicacao in (None, ""):
                    registros_sem_publicacao += 1
                    continue

                from datetime import datetime

                try:
                    data_publicacao = datetime.fromisoformat(
                        str(publicacao).replace("Z", "+00:00")
                    ).date()
                except ValueError as erro:
                    raise ValueError(
                        "dataPublicacaoPncp inválida no registro "
                        f"{registro['id_pncp']}."
                    ) from erro

                if data_inicial and data_publicacao < data_inicial:
                    continue
                if data_final and data_publicacao > data_final:
                    continue

            # Corrige a projeção local sem modificar a base recebida.
            registro = dict(registro)
            registro["data_publicacao"] = original.get("dataPublicacaoPncp")
            registro["modalidade_id"] = original.get("modalidadeId")

        atende = True

        for campo in (
            "uf", "municipio", "orgao", "modalidade", "fornecedor"
        ):
            esperado = filtros.get(campo)
            if esperado is not None:
                existente = normalizar_texto(registro.get(campo))
                if not existente or existente != normalizar_texto(esperado):
                    atende = False
                    break

        if not atende:
            continue

        if ano is not None and str(registro.get("ano_compra")) != str(ano):
            continue

        objeto = normalizar_texto(registro.get("objeto"))
        if termos and not any(normalizar_texto(t) in objeto for t in termos):
            continue

        if tem_limite:
            valor = converter_numero(registro.get(campo_valor))
            if valor is None:
                continue

            if minimo is not None:
                if valor < minimo or (
                    valor == minimo and not minimo_inclusivo
                ):
                    continue

            if maximo is not None:
                if valor > maximo or (
                    valor == maximo and not maximo_inclusivo
                ):
                    continue

        if resumo_tic is not None:
            classificacao = classificar_registro(registro)
            resumo_tic["registros_no_recorte"] += 1
            resumo_tic[classificacao["status"]] += 1

            if classificacao["status"] != "tic_proposto":
                continue

            if classificacao["tipo"] == "indeterminado":
                resumo_tic["tipo_indeterminado"] += 1

            if (
                tipo_tic != "todos"
                and classificacao["tipo"] != tipo_tic
            ):
                continue

            classificacoes_tic[registro["id_pncp"]] = classificacao

        selecionados.append(registro)

    selecionados.sort(key=lambda r: r["id_pncp"])
    total = len(selecionados)
    total_paginas = (
        (total + tamanho_pagina - 1) // tamanho_pagina
        if operacao == "listar" else 0
    )

    inicio = (pagina - 1) * tamanho_pagina
    apresentados = (
        selecionados[inicio:inicio + tamanho_pagina]
        if operacao == "listar" else []
    )

    return {
        "estrategia": "consulta_estruturada",
        "operacao": operacao,
        "filtros_aplicados": filtros,
        "campo_valor": campo_valor if tem_limite else None,
        "minimo_inclusivo": minimo_inclusivo,
        "maximo_inclusivo": maximo_inclusivo,
        "criterio_objeto": criterio_objeto,
        "criterio_tecnologia": criterio_tecnologia,
        "resumo_tecnologia": resumo_tic,
        "classificacoes_tecnologia": (
            [
                classificacoes_tic[r["id_pncp"]]
                for r in (
                    apresentados if operacao == "listar" else selecionados
                )
            ]
            if resumo_tic is not None else []
        ),
        "registros_sem_publicacao": registros_sem_publicacao,
        "fonte_data_publicacao": (
            "texto_integral.dataPublicacaoPncp"
            if filtrar_publicacao else None
        ),
        "total_base": len(base),
        "total": total,
        "campos": campos if operacao == "listar" else [],
        "registros": [
            {campo: registro.get(campo) for campo in campos}
            for registro in apresentados
        ],
        "referencias": [
            {
                "id_pncp": registro["id_pncp"],
                "fonte": registro.get("fonte_original"),
            }
            for registro in apresentados
        ],
        "fontes": sorted({
            str(r["fonte_original"])
            for r in selecionados if r.get("fonte_original")
        }),
        "pagina": pagina if operacao == "listar" else None,
        "tamanho_pagina": tamanho_pagina if operacao == "listar" else None,
        "total_paginas": total_paginas,
        "observacao": (
            (
                "Total operacional de propostas de TIC; "
                "não representa classificação humana validada. "
                "Casos ambíguos e tipos indeterminados exigem revisão. "
                if resumo_tic is not None else ""
            )
            + "Resultado restrito aos registros fornecidos. "
            "Ano da compra não representa ano de publicação."
        ),
    }
