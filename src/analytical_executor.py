"""Executa planos analíticos em registros normalizados, sem LLM."""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import unicodedata

from src.analytical_plan import CAMPOS, PlanoAnalitico


def _texto(valor):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(valor).strip().casefold())
        if unicodedata.category(c) != "Mn"
    )


def _converter(valor, tipo):
    if valor is None or isinstance(valor, str) and not valor.strip():
        return None

    if tipo == "numero":
        if isinstance(valor, (bool, float)):
            raise ValueError("Use Decimal, inteiro ou string decimal, não float.")
        try:
            numero = Decimal(str(valor).strip())
        except (InvalidOperation, ValueError) as erro:
            raise ValueError("Valor numérico inválido.") from erro
        if not numero.is_finite():
            raise ValueError("Valor numérico não finito.")
        return numero

    if tipo == "data":
        if not isinstance(valor, str):
            raise ValueError("Data exige string ISO AAAA-MM-DD.")
        return date.fromisoformat(valor.strip())

    if not isinstance(valor, str):
        raise ValueError("Campo textual exige string.")
    return valor.strip()


def _serializar(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def _compilar_filtros(filtros, tipos):
    preparados = []
    for filtro in filtros:
        tipo = tipos[filtro.campo]
        valores = (
            filtro.valor if filtro.operador == "em" else [filtro.valor]
        )
        convertidos = [_converter(valor, tipo) for valor in valores]
        if any(valor is None for valor in convertidos):
            raise ValueError("Filtro não pode conter valor vazio.")
        if tipo == "texto":
            convertidos = [_texto(valor) for valor in convertidos]
        preparados.append((filtro.campo, filtro.operador, convertidos))

    def corresponde(registro):
        for campo, operador, valores in preparados:
            atual = registro.get(campo)
            # Ausência de valor não comprova igualdade nem diferença.
            if atual is None:
                return False
            if tipos[campo] == "texto":
                atual = _texto(atual)
            alvo = valores[0]

            if operador == "igual":
                atende = atual == alvo
            elif operador == "diferente":
                atende = atual != alvo
            elif operador == "contem":
                atende = alvo in atual
            elif operador == "em":
                atende = atual in valores
            elif operador == "maior":
                atende = atual > alvo
            elif operador == "maior_igual":
                atende = atual >= alvo
            elif operador == "menor":
                atende = atual < alvo
            elif operador == "menor_igual":
                atende = atual <= alvo
            else:
                raise ValueError("Operador não implementado.")

            if not atende:
                return False
        return True

    return corresponde


def _medir(registros, tarefa):
    if tarefa.operacao == "contar" and not tarefa.campo:
        return {
            "valor": len(registros),
            "valores_ausentes": 0,
            "completo": True,
        }

    valores = [
        registro.get(tarefa.campo) for registro in registros
        if registro.get(tarefa.campo) is not None
    ]
    ausentes = len(registros) - len(valores)

    if tarefa.operacao == "contar":
        comparaveis = [
            _texto(valor) if isinstance(valor, str) else valor
            for valor in valores
        ]
        valor = (
            len(set(comparaveis)) if tarefa.distintos else len(valores)
        )
    elif tarefa.operacao == "somar":
        valor = (
            sum(valores, Decimal("0"))
            if valores or not registros
            else None
        )
    elif tarefa.operacao == "media":
        valor = sum(valores, Decimal("0")) / len(valores) if valores else None
    elif tarefa.operacao == "minimo":
        valor = min(valores) if valores else None
    elif tarefa.operacao == "maximo":
        valor = max(valores) if valores else None
    else:
        raise ValueError("Operação de medida não implementada.")

    return {
        "valor": _serializar(valor),
        "valores_presentes": len(valores),
        "valores_ausentes": ausentes,
        "completo": ausentes == 0,
    }


def executar_analitico(plano, registros):
    """Calcula sobre todos os registros; limites afetam somente a exibição."""
    if isinstance(plano, PlanoAnalitico):
        plano = plano.model_dump()
    plano = PlanoAnalitico.model_validate(plano)

    if plano.pendencias:
        raise ValueError("Plano possui pendências: " + "; ".join(plano.pendencias))
    if not isinstance(registros, list):
        raise ValueError("Registros devem ser uma lista.")

    tipos = CAMPOS[plano.fonte]
    utilizados = {f.campo for f in plano.filtros}
    for tarefa in plano.tarefas:
        utilizados.update(f.campo for f in tarefa.filtros)
        utilizados.update(tarefa.campos)
        utilizados.update(tarefa.agrupar_por)
        if tarefa.campo:
            utilizados.add(tarefa.campo)
        if tarefa.ordenar_por:
            utilizados.add(tarefa.ordenar_por)

    normalizados = []
    for registro in registros:
        if not isinstance(registro, dict):
            raise ValueError("Registro inválido.")
        if utilizados - registro.keys():
            raise ValueError("Registro não possui os campos necessários ao plano.")
        normalizados.append({
            campo: _converter(registro[campo], tipos[campo])
            for campo in utilizados
        })

    filtro_global = _compilar_filtros(plano.filtros, tipos)
    selecionados = [r for r in normalizados if filtro_global(r)]
    resultados = {}

    with localcontext() as contexto:
        contexto.prec = 50

        for tarefa in plano.tarefas:
            filtro_tarefa = _compilar_filtros(tarefa.filtros, tipos)
            linhas = [r for r in selecionados if filtro_tarefa(r)]
            resultado = {
                "id": tarefa.id,
                "operacao": tarefa.operacao,
                "campo": tarefa.campo,
                "filtros": [f.model_dump() for f in tarefa.filtros],
                "total_registros": len(linhas),
            }

            if tarefa.operacao == "listar":
                if tarefa.ordenar_por:
                    campo = tarefa.ordenar_por
                    presentes = [r for r in linhas if r.get(campo) is not None]
                    ausentes = [r for r in linhas if r.get(campo) is None]
                    presentes.sort(
                        key=lambda r: (
                            _texto(r[campo])
                            if tipos[campo] == "texto" else r[campo]
                        ),
                        reverse=tarefa.ordem == "decrescente",
                    )
                    linhas = presentes + ausentes

                if tarefa.distintos:
                    vistos = set()
                    unicos = []
                    for registro in linhas:
                        chave = tuple(registro.get(c) for c in tarefa.campos)
                        if chave not in vistos:
                            vistos.add(chave)
                            unicos.append(registro)
                    linhas = unicos
                    resultado["distintos"] = True
                    resultado["total_resultados"] = len(linhas)

                resultado.update({
                    "registros": [
                        {campo: _serializar(r.get(campo)) for campo in tarefa.campos}
                        for r in linhas[:tarefa.limite]
                    ],
                    "campos": tarefa.campos,
                    "limite": tarefa.limite,
                    "truncado": len(linhas) > tarefa.limite,
                })

            elif tarefa.agrupar_por:
                grupos = defaultdict(list)
                for registro in linhas:
                    chave = tuple(registro.get(c) for c in tarefa.agrupar_por)
                    grupos[chave].append(registro)

                medidas = [
                    {
                        **{
                            campo: _serializar(valor)
                            for campo, valor in zip(tarefa.agrupar_por, chave)
                        },
                        "total_registros": len(grupo),
                        **_medir(grupo, tarefa),
                    }
                    for chave, grupo in grupos.items()
                ]
                resultado.update({
                    "agrupar_por": tarefa.agrupar_por,
                    "grupos": medidas[:tarefa.limite],
                    "total_grupos": len(medidas),
                    "truncado": len(medidas) > tarefa.limite,
                })
            else:
                resultado.update(_medir(linhas, tarefa))

            resultados[tarefa.id] = resultado

        comparacoes = []
        for comparacao in plano.comparacoes:
            esquerda = resultados[comparacao.esquerda]
            direita = resultados[comparacao.direita]
            a, b = esquerda["valor"], direita["valor"]
            motivo = None
            valor = None

            if a is None or b is None:
                motivo = "Um dos resultados não possui valor calculável."
            else:
                a, b = Decimal(str(a)), Decimal(str(b))
                if comparacao.operacao == "diferenca":
                    valor = a - b
                elif b == 0:
                    motivo = "Denominador igual a zero."
                elif comparacao.operacao == "razao":
                    valor = a / b
                else:
                    valor = a / b * Decimal("100")

            comparacoes.append({
                **comparacao.model_dump(),
                "valor": _serializar(valor),
                "motivo": motivo,
                "completo": (
                    motivo is None
                    and esquerda["completo"]
                    and direita["completo"]
                ),
            })

    return {
        "fonte": plano.fonte,
        "plano": plano.model_dump(),
        "total_base": len(registros),
        "total_apos_filtros": len(selecionados),
        "resultados": list(resultados.values()),
        "comparacoes": comparacoes,
        "precisao_decimal": 50,
    }
