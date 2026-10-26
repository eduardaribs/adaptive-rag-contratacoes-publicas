"""Classificação operacional de TIC com evidência rastreável."""

import re

from src.structured_query import normalizar_texto


VERSAO_CRITERIO = "tic-contextual-v3"

CAMPOS_PRIORITARIOS = (
    "objeto",
    "descricao_item",
    "descricao_servico",
    "especificacao",
)

EXPRESSOES_TIC = (
    "tecnologia da informacao",
    "tecnologia da informacao e comunicacao",
    "seguranca da informacao",
    "ciberseguranca",
    "computacao em nuvem",
    "licenca de software",
    "licencas de software",
    "desenvolvimento de sistemas",
    "suporte de ti",
    "suporte tecnico de informatica",
    "servicos de informatica",
    "equipamentos de informatica",
    "materiais de informatica",
    "material de informatica",
    "material de consumo de informatica",
    "software como servico",
    "software de como servico",
)

# Expressões que contextualizam os indicadores ambíguos.
PADROES_CONTEXTUAIS = (
    r"\blink de internet\b",
    r"\b(?:aquisicao|fornecimento|contratacao|licencas?|licenciamento)"
    r"\b.{0,180}\bsoftwares?\b",
    r"\bsoftwares?\b.{0,100}\b(?:licencas?|licenciamento|saas)\b",
    r"\bservidor(?:es)?\s+(?:rack|de dados|de rede|virtual|vps)\b",
    r"\brede(?:s)?\s+(?:de dados|de computadores|local|corporativa)\b",
    r"\barmazenamento\s+(?:de dados|digital|em nuvem)\b",
    r"\b(?:aquisicao|fornecimento|locacao|outsourcing)\b"
    r".{0,180}\b(?:computadores?|notebooks?|microcomputadores?)\b",
    r"\b(?:servicos?|solucao|contratacao)\b"
    r".{0,180}\b(?:telecomunicacoes|datacenter|data center|colocation)\b",
    r"\b(?:hospedagem|servidor)\b.{0,100}\b(?:vps|home.page|web)\b",
    r"\bvirtualizacao\b.{0,100}\b(?:midias|servidores|dados)\b",
    r"\bcomunicacao multimidia\b.{0,100}\b(?:mpls|internet|backbone)\b",
)

INDICADORES = (
    "software", "softwares", "computador", "computadores",
    "servidor", "armazenamento", "rede", "telecomunicacoes",
    "nuvem", "informatica", "digital", "eletronico",
    "sistema", "tecnologia", "tic", "datacenter",
    "data center", "virtualizacao", "notebook", "notebooks",
)

CONTEXTO_ADMINISTRATIVO = (
    "jovem aprendiz",
    "programa de aprendizagem",
    "recrutamento",
)


def contem(texto, expressao):
    return bool(re.search(
        r"(?<!\w)" + re.escape(expressao) + r"(?!\w)",
        texto,
    ))


def classificar_registro(registro):
    """Propõe classificação sem alterar o registro recebido.

    Examina campos prioritários disponíveis. Campos auxiliares e o nome
    da instituição não comprovam, sozinhos, aquisição de TIC.
    A classificação operacional não equivale a revisão humana completa.
    """
    evidencias = []
    indicadores = []
    campos_presentes = []
    administrativo = False

    for campo in CAMPOS_PRIORITARIOS:
        original = str(registro.get(campo) or "").strip()
        if not original:
            continue

        campos_presentes.append(campo)
        texto = re.sub(r"\s+", " ", normalizar_texto(original))

        termos = [
            termo for termo in INDICADORES
            if contem(texto, termo)
        ]
        indicadores.extend(termos)

        administrativo = administrativo or any(
            contem(texto, termo)
            for termo in CONTEXTO_ADMINISTRATIVO
        )

        expressoes = [
            expressao for expressao in EXPRESSOES_TIC
            if contem(texto, expressao)
        ]
        contextos = [
            correspondencia.group(0)
            for padrao in PADROES_CONTEXTUAIS
            for correspondencia in re.finditer(padrao, texto)
        ]

        if expressoes or contextos:
            evidencias.append({
                "campo": campo,
                "texto": original,
                "expressoes": expressoes,
                "contextos": contextos,
            })

    indicadores = list(dict.fromkeys(indicadores))

    if not campos_presentes:
        status = "revisao"
        motivo = "Campos prioritários ausentes."
    elif administrativo and (evidencias or indicadores):
        status = "revisao"
        motivo = (
            "Contexto administrativo com menção a TIC; "
            "é necessário distinguir o objeto da instituição."
        )
    elif evidencias:
        status = "tic_proposto"
        motivo = (
            "Campo prioritário contém expressão ou contexto "
            "operacional específico de bem ou serviço de TIC."
        )
    elif indicadores:
        status = "revisao"
        motivo = (
            "Indicadores encontrados sem contexto suficiente "
            "pelas regras operacionais."
        )
    else:
        status = "sem_indicio"
        motivo = (
            "Nenhum indicador reconhecido nos campos disponíveis. "
            "Isso não comprova ausência de TIC."
        )

    principal = evidencias[0] if evidencias else None
    campo_evidencia = (
        principal["campo"] if principal
        else (campos_presentes[0] if campos_presentes else "objeto")
    )
    evidencia = str(registro.get(campo_evidencia) or "")
    texto_principal = normalizar_texto(evidencia)

    tipo = (
        _identificar_tipo_tic(texto_principal)
        if status == "tic_proposto" else "indeterminado"
    )

    return {
        "id_pncp": registro.get("id_pncp"),
        "status": status,
        "tipo": tipo,
        "criterio_versao": VERSAO_CRITERIO,
        "campo_evidencia": campo_evidencia,
        "evidencia": evidencia,
        "expressoes_contextuais": list(dict.fromkeys(
            expressao
            for item in evidencias
            for expressao in item["expressoes"]
        )),
        "indicadores": indicadores,
        "evidencias_classificacao": evidencias,
        "campos_analisados": campos_presentes,
        "motivo": motivo,
        "fonte": registro.get("fonte_original"),
    }


def _identificar_tipo_tic(texto):
    """Identifica o objeto fornecido, não apenas o verbo fornecimento."""
    texto = re.sub(r"\s+", " ", texto)

    bem_fisico = bool(re.search(
        r"\b(?:aquisicao|compra|fornecimento)\b.{0,120}"
        r"\b(?:computadores?|notebooks?|microcomputadores?|"
        r"servidores?|equipamentos|memorias|ssds?|chromebooks?)\b",
        texto,
    ))

    # Aquisição de solução com serviços associados é objeto misto.
    bem_fisico = bem_fisico or bool(re.search(
        r"\b(?:aquisicao|compra) de (?:uma )?solucao\b",
        texto,
    ))

    servico_especifico = bool(re.search(
        r"\b(?:saas|outsourcing|colocation)\b"
        r"|\bsoftware (?:de )?como (?:um )?servico\b"
        r"|\blink de internet\b"
        r"|\bcomunicacao multimidia\b"
        r"|\bservicos? de telecomunicacoes\b"
        r"|\bservicos? de desenvolvimento de software\b"
        r"|\bservico gerenciado de seguranca da informacao\b"
        r"|\bservicos? tecnicos(?: especializados)? "
        r"(?:continuos )?de operacao de infraestrutura\b",
        texto,
    ))

    servico_explicito = bool(re.search(
        r"\bprestacao (?:dos? )?servicos?\b"
        r"|\bcontratacao (?:de |do |dos )?servicos?\b"
        r"|\bservicos? de suporte\b",
        texto,
    ))

    # Outsourcing e locação não significam aquisição dos equipamentos.
    locacao = bool(re.search(
        r"\b(?:locacao|outsourcing)\b",
        texto,
    ))
    if locacao:
        bem_fisico = False

    servico = servico_especifico or servico_explicito

    if bem_fisico and servico:
        return "indeterminado"

    if servico:
        return "servico_proposto"

    if bem_fisico:
        return "bem_proposto"

    if re.search(
        r"\b(?:licencas?|licenciamento)\b",
        texto,
    ):
        # Não presume a natureza de licenças temporárias ou assinaturas.
        if re.search(r"\b(?:perpetuas?|compra unica)\b", texto):
            return "bem_proposto"
        return "indeterminado"

    if re.search(
        r"\b(?:aquisicao|compra|fornecimento)\b",
        texto,
    ):
        return "bem_proposto"

    return "indeterminado"
