"""Apresentação determinística de resultados agrupados do executor."""

from decimal import Decimal, InvalidOperation


ROTULOS = {
    "situacao_item": "Situação",
    "fornecedor": "Fornecedor",
    "categoria": "Categoria",
    "unidade_responsavel": "Unidade responsável",
    "uasg": "UASG",
    "descricao": "Descrição",
    "unidade_fornecimento": "Unidade de fornecimento",
}

OPERACOES = {
    "contar": "Quantidade",
    "somar": "Soma",
    "media": "Média",
    "minimo": "Mínimo",
    "maximo": "Máximo",
}


def _celula(valor):
    if valor is None:
        return "Não informado"
    return (
        str(valor)
        .replace("\\", "\\\\")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "&#124;")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _numero(valor, operacao):
    if valor is None:
        return "Não informado"
    if isinstance(valor, bool) or not isinstance(valor, (int, str, Decimal)):
        raise ValueError("Resultado numérico incompatível.")

    try:
        numero = Decimal(str(valor))
    except InvalidOperation as erro:
        raise ValueError("Resultado numérico inválido.") from erro

    if not numero.is_finite():
        raise ValueError("Resultado numérico não finito.")

    if operacao == "contar":
        if numero != numero.to_integral_value() or numero < 0:
            raise ValueError("Contagem deve ser inteira e não negativa.")
        return str(int(numero))

    # Preserva a precisão recebida; muda apenas o separador decimal.
    return format(numero, "f").replace(".", ",")


def renderizar_agrupamento(resultado):
    """
    Converte um resultado agrupado em tabela Markdown e dados da interface.

    Não interpreta perguntas, não recalcula valores e não completa grupos.
    """
    agrupadores = resultado.get("agrupar_por")
    grupos = resultado.get("grupos")
    operacao = resultado.get("operacao")

    if (
        not isinstance(agrupadores, list)
        or not agrupadores
        or any(not isinstance(campo, str) or not campo for campo in agrupadores)
        or len(agrupadores) != len(set(agrupadores))
    ):
        raise ValueError("Agrupadores ausentes ou inválidos.")
    if not isinstance(grupos, list) or operacao not in OPERACOES:
        raise ValueError("Resultado agrupado inválido.")

    rotulo_medida = OPERACOES[operacao]
    campo = resultado.get("campo")
    if campo:
        rotulo_medida += " de " + ROTULOS.get(
            campo, campo.replace("_", " ")
        )
    if resultado.get("distintos"):
        rotulo_medida += " — valores distintos"

    colunas = [
        ROTULOS.get(campo, campo.replace("_", " ").capitalize())
        for campo in agrupadores
    ] + [rotulo_medida]

    linhas = []
    for grupo in grupos:
        if not isinstance(grupo, dict):
            raise ValueError("Grupo inválido.")
        if any(campo not in grupo for campo in agrupadores):
            raise ValueError("Grupo sem um dos campos de agrupamento.")
        if "valor" not in grupo:
            raise ValueError("Grupo sem resultado calculado.")
        linhas.append(
            [_celula(grupo[campo]) for campo in agrupadores]
            + [_numero(grupo["valor"], operacao)]
        )

    partes = [
        "| " + " | ".join(_celula(c) for c in colunas) + " |",
        "| " + " | ".join("---" for _ in colunas) + " |",
    ]
    partes.extend(
        "| " + " | ".join(linha) + " |"
        for linha in linhas
    )

    notas = []
    if not grupos:
        notas.append("Nenhum grupo encontrado para os critérios aplicados.")
    if resultado.get("truncado"):
        notas.append(
            f"Exibidos {len(grupos)} de "
            f"{resultado.get('total_grupos', 'quantidade não informada')} grupos."
        )
    if any(grupo.get("completo") is False for grupo in grupos):
        notas.append(
            "Há grupos com valores ausentes; consulte os detalhes do cálculo."
        )

    markdown = "\n".join(partes)
    if notas:
        markdown += "\n\n" + "\n\n".join(notas)

    return {
        "colunas": colunas,
        "linhas": linhas,
        "markdown": markdown,
        "notas": notas,
    }
