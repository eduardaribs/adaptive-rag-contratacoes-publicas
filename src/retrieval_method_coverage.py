"""Preserva candidatos dos dois métodos sem alterar seus scores."""


def cobrir_metodos(ranking, densos, lexicais, top_k):
    if top_k < 2 or not ranking or not densos or not lexicais:
        return ranking

    elegiveis = {item["chunk_id"] for item in ranking}
    escolhidos = []

    def reservar(lista, quantidade):
        if quantidade <= 0:
            return
        adicionados = 0
        for item in lista:
            identificador = item["chunk_id"]
            if identificador in elegiveis and identificador not in escolhidos:
                escolhidos.append(identificador)
                adicionados += 1
                if adicionados >= quantidade:
                    break

    reservar(lexicais, (top_k + 1) // 2)
    reservar(densos, max(0, top_k - len(escolhidos)))

    for item in ranking:
        if len(escolhidos) >= top_k:
            break
        if item["chunk_id"] not in escolhidos:
            escolhidos.append(item["chunk_id"])

    ids = set(escolhidos[:top_k])
    return (
        [item for item in ranking if item["chunk_id"] in ids]
        + [item for item in ranking if item["chunk_id"] not in ids]
    )
