from pathlib import Path

"""Escopo de recuperação para atas explicitamente identificadas."""

import json
import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto)).lower()
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"\s+", " ", texto).strip()


PADRAO_ATA = re.compile(
    r"\bata\s+"
    r"(?:(?:de\s+registro\s+de\s+precos)\s*[-–]?\s*)?"
    r"(?:(?:sei)\s*)?"
    r"(?:n(?:o|º|°|\.)?\s*)?"
    r"0*(\d+)\s*/\s*(20\d{2})(?!\d)"
)

PADRAO_PROCESSO = re.compile(
    r"\bprocesso(?:\s+administrativo)?\s*"
    r"(?:n[.\sº°o]*\s*)?"
    r"(\d{5}\s*\.\s*\d{6}\s*/\s*\d{4}\s*-\s*\d{2})"
)


def escopar_ata(pergunta, chunks_por_id, identificar_natureza):
    """Retorna None sem ata explícita, ou IDs elegíveis e sua justificativa.

    Documentos sem correspondência ou com identidade ambígua retornam
    conjunto vazio. Um vínculo estruturado exige processo exato.
    """
    pedido = PADRAO_ATA.search(normalizar(pergunta))
    if not pedido:
        return None

    identidade = tuple(int(valor) for valor in pedido.groups())
    documentos = {}

    for identificador, chunk in chunks_por_id.items():
        if identificar_natureza(chunk) != "conversacional":
            continue

        fonte = (chunk.get("metadata") or {}).get("source_file")
        if fonte:
            documentos.setdefault(fonte, []).append(
                (identificador, chunk)
            )

    fontes = []
    for fonte, paginas in documentos.items():
        identidades = {
            tuple(int(valor) for valor in achado.groups())
            for _, chunk in paginas
            for achado in PADRAO_ATA.finditer(
                normalizar(chunk.get("text", ""))
            )
        }
        if identidade in identidades:
            fontes.append(fonte)

    if len(fontes) != 1:
        return {
            "ids": set(),
            "fontes": sorted(fontes),
            "processos": [],
            "motivo": "Ata não localizada de forma unívoca.",
        }

    fonte = fontes[0]
    paginas = documentos[fonte]
    ids = {identificador for identificador, _ in paginas}

    processos = {
        re.sub(r"\D", "", achado.group(1))
        for _, chunk in paginas
        for achado in PADRAO_PROCESSO.finditer(
            normalizar(chunk.get("text", ""))
        )
    }

    for identificador, chunk in chunks_por_id.items():
        if identificar_natureza(chunk) != "estruturada":
            continue

        try:
            registro = json.loads(chunk.get("text", ""))
        except (TypeError, json.JSONDecodeError):
            continue

        if not isinstance(registro, dict):
            continue

        processo = re.sub(r"\D", "", str(registro.get("processo") or ""))
        if processo and processo in processos:
            ids.add(identificador)

    return {
        "ids": ids,
        "fontes": [fonte],
        "processos": sorted(processos),
        "motivo": "Ata identificada por número/ano; vínculo por processo exato.",
    }


PADRAO_PROCESSO_ALFANUMERICO = re.compile(
    r"\bprocesso\s+(?:ficticio\s*)?[: ]*"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)+)(?![\w-])"
)


def escopar_processo_alfanumerico(
    pergunta, chunks_por_id, identificar_natureza,
):
    """Limita fontes conversacionais por identificador explícito exato."""
    pedidos = {
        achado.group(1)
        for achado in PADRAO_PROCESSO_ALFANUMERICO.finditer(
            normalizar(pergunta)
        )
    }
    if not pedidos:
        return None

    if len(pedidos) != 1:
        return {
            "ids": set(),
            "fontes": [],
            "processos": sorted(pedidos),
            "motivo": "Mais de um processo informado; escopo não definido.",
        }

    processo = next(iter(pedidos))
    padrao = re.compile(
        r"(?<![\w-])" + re.escape(processo) + r"(?![\w-])"
    )

    documentos = {}
    for identificador, chunk in chunks_por_id.items():
        if identificar_natureza(chunk) != "conversacional":
            continue
        fonte = (chunk.get("metadata") or {}).get("source_file")
        if fonte:
            documentos.setdefault(fonte, []).append(
                (identificador, chunk)
            )

    fontes = [
        fonte
        for fonte, partes in documentos.items()
        if any(
            padrao.search(normalizar(chunk.get("text", "")))
            for _, chunk in partes
        )
    ]

    if len(fontes) != 1:
        return {
            "ids": set(),
            "fontes": sorted(fontes),
            "processos": [processo],
            "motivo": "Processo não localizado de forma unívoca.",
        }

    fonte = fontes[0]
    return {
        "ids": {
            identificador for identificador, _ in documentos[fonte]
        },
        "fontes": [fonte],
        "processos": [processo],
        "motivo": "Documento identificado por processo alfanumérico exato.",
    }


def escopar_documento(pergunta, chunks_por_id, identificar_natureza):
    """Preserva o escopo de atas e reconhece processos alfanuméricos."""
    ata = escopar_ata(pergunta, chunks_por_id, identificar_natureza)
    if ata is not None:
        return ata
    processo = escopar_processo_alfanumerico(
        pergunta, chunks_por_id, identificar_natureza,
    )
    if processo is not None:
        return processo
    return escopar_pregao(
        pergunta, chunks_por_id, identificar_natureza,
    )


_PADRAO_PREGAO = re.compile(
    r"\b(?:pe|pregao(?:\s+eletronico)?)\s*"
    r"(?:n[.\sº°o]*\s*)?"
    r"(\d+(?:\.\d+)*)\s*/\s*(\d+)"
    r"(?:\s*/\s*(\d+))?(?![\d/])"
)


def _identidades_pregao(texto):
    return {
        tuple(int(v.replace(".", "")) for v in achado.groups() if v is not None)
        for achado in _PADRAO_PREGAO.finditer(normalizar(texto))
    }


def escopar_pregao(pergunta, chunks_por_id, identificar_natureza):
    """Preserva normas gerais e exige referência exata nas demais fontes."""
    pedidos = _identidades_pregao(pergunta)
    if not pedidos:
        return None
    documentos = {}
    ids = set()
    for identificador, chunk in chunks_por_id.items():
        if identificar_natureza(chunk) == "normativa":
            ids.add(identificador)
            continue
        fonte = (chunk.get("metadata") or {}).get("source_file")
        if fonte:
            documentos.setdefault(fonte, []).append((identificador, chunk))
    fontes = []
    for fonte, partes in documentos.items():
        identidades = set()
        for _, chunk in partes:
            identidades.update(_identidades_pregao(chunk.get("text", "")))
        referencia_nome = re.search(
            r"(?:^|_)pe_(\d+)_(\d+)_(20\d{2})(?:[_.]|$)",
            normalizar(Path(fonte).name),
        )
        if referencia_nome:
            identidades.add(tuple(int(v) for v in referencia_nome.groups()))
        if len(pedidos) == 1 and identidades == pedidos:
            fontes.append(fonte)
            ids.update(identificador for identificador, _ in partes)
    return {
        "ids": ids, "fontes": sorted(fontes), "processos": [],
        "motivo": (
            "Referência exata de pregão nas fontes vinculadas; "
            "normas preservadas apenas como fundamento geral. "
            "Similaridade textual não comprova vínculo."
        ),
    }
