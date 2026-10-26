"""Planejamento conservador dos resumos agregados suportados."""

import re


def planejar_agregada(texto, plano):
    """Recebe texto normalizado e retorna plano ou None.

    Reconhece formas explícitas de resumo completo dos dois arquivos.
    Não implementa filtros arbitrários ou médias. M01 verifica vínculos por identificadores.
    """
    texto = _normalizar_reformulacao(texto)

    menciona_pca = bool(
        re.search(r"\bpca\b", texto)
        or "plano de contratacoes anual" in texto
    )
    menciona_pe = bool(
        re.search(r"\bpe\s*038/26/2026\b", texto)
    )
    pede_calculo = bool(
        re.search(r"\b(?:quantos|quantas|soma|total|calcule|media|resuma|resumo)\b", texto)
    )

    if not pede_calculo or not (menciona_pca or menciona_pe):
        return None

    # As expressões completas evitam ignorar critérios adicionais.
    pca_suportado = re.fullmatch(
        r"quantos itens constam no "
        r"(?:plano de contratacoes anual|pca) "
        r"do estado do rio de janeiro para 2026 "
        r"e qual e o valor total estimado informado[?. ]*",
        texto,
    )
    itens_suportado = re.fullmatch(
        r"no pe\s*038/26/2026,?\s+"
        r"quantos itens foram homologados,?\s+fracassados e desertos "
        r"e qual (?:foi|e) a soma dos valores homologados[?. ]*",
        texto,
    )

    m01_suportado = re.fullmatch(
        r"com base no pe\s*038/26/2026,?\s+"
        r"informe quantos itens foram homologados,?\s+fracassados e desertos,?\s+"
        r"calcule o valor total homologado e verifique se existe alguma "
        r"informacao relacionada a essa contratacao nas demais naturezas "
        r"de evidencia disponiveis no corpus[?. ]*",
        texto,
    )

    if m01_suportado:
        return {
            **plano,
            "bases": ["agregada"],
            "estrategia": "consulta_agregada",
            "operacao": "resumir_itens_vinculos",
            "filtros": {
                "id_contratacao_pncp": "42498600000171-1-000757/2026",
            },
            "processo_informado": "PE 038/26/2026",
            "rotas_complementares_a_verificar": [
                "estruturada", "conversacional", "normativa",
            ],
            "metodo_vinculo": "ID PNCP completo ou URL específica do edital",
        }

    if pca_suportado:
        return {
            **plano,
            "bases": ["agregada"],
            "estrategia": "consulta_agregada",
            "operacao": "resumir_pca",
            "filtros": {},
            "recorte_fonte": {
                "documento": "PCA",
                "uf": "RJ",
                "ano": 2026,
                "observacao": (
                    "Recorte associado ao arquivo PCA disponibilizado; "
                    "o cálculo utiliza todas as suas linhas."
                ),
            },
        }

    if itens_suportado:
        return {
            **plano,
            "bases": ["agregada"],
            "estrategia": "consulta_agregada",
            "operacao": "resumir_itens",
            "filtros": {
                "id_contratacao_pncp": "42498600000171-1-000757/2026",
            },
            "processo_informado": "PE 038/26/2026",
            "referencia_mapeamento": (
                "data/raw/v3/agregada/itens_pe_038_26_2026.csv"
            ),
        }

    return {
        **plano,
        "bases": ["agregada"],
        "estrategia": "esclarecimento",
        "operacao": "esclarecer",
        "necessita_esclarecimento": True,
        "pergunta_esclarecimento": (
            "Nesta etapa, a consulta agregada oferece o resumo completo "
            "do PCA RJ 2026 ou a contagem por situação e soma homologada "
            "do PE 038/26/2026. Outros filtros, operações e cruzamentos "
            "de fontes ainda não estão conectados. "
            "Você deseja um desses resumos completos?"
        ),
    }


def _normalizar_reformulacao(texto):
    """Reconhece reformulações completas dos resumos disponíveis.

    Não remove filtros adicionais nem pedidos não suportados.
    """
    texto = re.sub(r"\s+", " ", texto).strip()


    # Resumo completo com vínculos, sem critérios adicionais.
    if re.fullmatch(
        r"resuma (?:o )?pe\s*038/26/2026 e "
        r"(?:verifique|confira) (?:os )?vinculos "
        r"(?:nas|com as) demais naturezas "
        r"(?:de evidencia )?do corpus[?. ]*",
        texto,
    ):
        return (
            "com base no pe 038/26/2026, informe quantos itens foram "
            "homologados, fracassados e desertos, calcule o valor total "
            "homologado e verifique se existe alguma informacao "
            "relacionada a essa contratacao nas demais naturezas "
            "de evidencia disponiveis no corpus"
        )

    alternativas = (
        (
            r"(?:qual e o total|qual o total|informe o total) de itens "
            r"(?:do|no) pca (?:do estado do rio de janeiro|rj) "
            r"(?:de|para) 2026 e "
            r"(?:qual e |qual |informe )?"
            r"(?:o )?valor total estimado[?. ]*",
            "quantos itens constam no pca do estado do rio de janeiro "
            "para 2026 e qual e o valor total estimado informado",
        ),
        (
            r"(?:resuma|mostre o resumo de|apresente o resumo de) "
            r"(?:o )?pe\s*038/26/2026[:;, ]+"
            r"quantidade de itens homologados, fracassados e desertos "
            r"e (?:a )?(?:soma|valor total) "
            r"(?:dos valores homologados|homologado)[?. ]*",
            "no pe 038/26/2026, quantos itens foram homologados, "
            "fracassados e desertos e qual foi a soma "
            "dos valores homologados",
        ),
        (
            r"(?:resuma|apresente o resumo de) (?:o )?"
            r"pe\s*038/26/2026[:;, ]+"
            r"quantidade de itens homologados, fracassados e desertos, "
            r"(?:soma|valor total) homologad[oa] e "
            r"(?:verifique|confira) "
            r"(?:os )?vinculos (?:nas|com as) demais "
            r"naturezas (?:de evidencia )?do corpus[?. ]*",
            "com base no pe 038/26/2026, informe quantos itens foram "
            "homologados, fracassados e desertos, calcule o valor total "
            "homologado e verifique se existe alguma informacao "
            "relacionada a essa contratacao nas demais naturezas "
            "de evidencia disponiveis no corpus",
        ),
    )

    for padrao, pergunta_canonica in alternativas:
        if re.fullmatch(padrao, texto):
            return pergunta_canonica

    return texto
