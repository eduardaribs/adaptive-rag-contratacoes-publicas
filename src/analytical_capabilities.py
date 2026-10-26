"""Limites conhecidos de fontes; não substitui interpretação semântica."""

import re
import unicodedata


def _normalizar(texto):
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caractere) != "Mn"
    )


# São capacidades dos arquivos, não perguntas com respostas cadastradas.
LIMITES_ITENS_PE = (
    (
        "assinatura",
        r"\bassinatur[ao]s?\b|\bassinad[oa]s?\b",
        "data ou informação de assinatura do contrato",
    ),
    (
        "pagamento",
        r"\bpagamentos?\b|\bpag[oa]s?\b|\bquitad[oa]s?\b",
        "comprovação de pagamento",
    ),
    (
        "entrega",
        r"\bentregas?\b|\bentregu[eo]s?\b|\brecebiment[oa]s?\b",
        "comprovação ou data de entrega e recebimento",
    ),
    (
        "valor_estimado",
        r"\bvalor(?:es)?\s+(?:total(?:is)?\s+|unitari[oa]s?\s+)?"
        r"estimad[oa]s?\b",
        "valores estimados",
    ),
)


def verificar_limites_conhecidos(pergunta):
    """
    Sinaliza menções a informações ausentes no arquivo do PE identificado.

    A verificação é conservadora: uma menção pode ser explicativa,
    negativa ou parte de um pedido documental. Por isso, ela produz
    esclarecimento, sem afirmar que toda a pergunta seja impossível.

    Ausência de alerta não comprova que a pergunta inteira foi atendida.
    """
    texto = _normalizar(pergunta)

    # Não atribui este arquivo a outro processo nem ao PCA.
    if not re.search(r"\bpe\s*038\s*/\s*26\s*/\s*2026\b", texto):
        return None

    # Mais de um PE explícito exige interpretação de escopo.
    processos = re.findall(
        r"\bpe\s*(\d+\s*/\s*\d+\s*/\s*\d{4})\b", texto
    )
    processos = {
        re.sub(r"\s+", "", processo)
        for processo in processos
    }
    if processos != {"038/26/2026"}:
        return None

    alertas = []
    for conceito, padrao, descricao in LIMITES_ITENS_PE:
        correspondencia = re.search(padrao, texto)
        if correspondencia:
            alertas.append({
                "conceito": conceito,
                "mencao_normalizada": correspondencia.group(),
                "informacao_ausente_no_arquivo": descricao,
            })

    if not alertas:
        return None

    ausencias = "; ".join(
        alerta["informacao_ausente_no_arquivo"]
        for alerta in alertas
    )
    return {
        "fonte": "itens_pe",
        "alertas": alertas,
        "mensagem": (
            "A pergunta menciona informações que o arquivo de itens do "
            f"PE 038/26/2026 não oferece: {ausencias}. "
            "Esse arquivo permite consultar a situação dos itens, "
            "a data de homologação e os valores homologados. "
            "Não vou apresentar uma contagem ou soma que ignore "
            "a condição mencionada. Para atender esse critério, "
            "é necessário fornecer a informação correspondente "
            "ou esclarecer se ela deve ser desconsiderada. "
            "Este limite se refere ao arquivo de itens; não comprova "
            "ausência dessas informações em outros documentos."
        ),
    }
