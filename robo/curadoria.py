"""Filtra e pontua as ofertas segundo o checklist do playbook do Papai Achou."""

import math

from robo import semelhanca, config, historico, regras


def _num(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _opcional(valor):
    """Número ou None quando a informação não veio (ex.: planilha sem a coluna de nota)."""
    if valor is None or valor == "":
        return None
    return _num(valor, None)


def _loja_oficial(tipo):
    """shopType vem como lista de códigos; 1 = loja oficial (Shopee Mall)."""
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return any(str(t) == "1" for t in tipos)


def normalizar(no):
    """Converte o produto (Shopee, Magalu ou Mercado Livre) para um formato simples, com números de verdade."""
    preco = _num(no.get("priceMin"))
    desconto = _opcional(no.get("priceDiscountRate"))
    preco_antigo = _opcional(no.get("_precoAntigo"))  # a planilha às vezes traz o preço original
    if not preco_antigo or preco_antigo <= preco:
        preco_antigo = round(preco / (1 - desconto / 100), 2) if desconto and 0 < desconto < 100 else None
    plataforma = no.get("_plataforma") or "Shopee"
    prefixo = "" if plataforma == "Shopee" else plataforma.lower().replace(" ", "") + "-"
    return {
        "chave": f"{prefixo}{no.get('shopId')}-{no.get('itemId')}",
        "plataforma": plataforma,
        "forma_preco": no.get("_formaPreco") or "",
        "avaliacoes": None if _opcional(no.get("_avaliacoes")) is None else int(_num(no.get("_avaliacoes"))),
        "nome": (no.get("productName") or "").strip(),
        "preco": preco,
        "preco_antigo": preco_antigo,
        "desconto": desconto,
        "nota": _opcional(no.get("ratingStar")),
        "vendas": None if _opcional(no.get("sales")) is None else int(_num(no.get("sales"))),
        "comissao_taxa": _opcional(no.get("commissionRate")),
        "comissao_valor": _num(no.get("commission")),
        "foto": no.get("imageUrl"),
        "link": no.get("offerLink") or no.get("productLink"),
        "loja": no.get("shopName") or "",
        "loja_oficial": _loja_oficial(no.get("shopType")),
        "categoria": no.get("_categoria") or "Presentes",
    }


def motivo_reprovacao(oferta):
    bloqueio = regras.motivo_bloqueio(oferta["nome"])
    if bloqueio:
        return bloqueio
    # Informação que não veio (None) não reprova: a planilha da Shopee nem sempre traz tudo.
    if oferta["nota"] is not None and oferta["nota"] < config.NOTA_MINIMA:
        return "nota baixa"
    if oferta["vendas"] is not None and oferta["vendas"] < config.VENDAS_MINIMAS:
        return "poucas vendas"
    if oferta.get("avaliacoes") is not None and oferta["avaliacoes"] < config.AVALIACOES_MINIMAS:
        return "poucas avaliações"
    if oferta["desconto"] is not None and oferta["desconto"] < config.DESCONTO_MINIMO:
        return "desconto pequeno"
    if oferta["comissao_taxa"] is not None and oferta["comissao_taxa"] < config.COMISSAO_MINIMA:
        return "comissão baixa"
    if not config.PRECO_MINIMO <= oferta["preco"] <= config.PRECO_MAXIMO:
        return "fora da faixa de preço"
    if not oferta["link"]:
        return "sem link"
    return None


def pontuar(oferta):
    """Nota de 0 a ~100: vendas e desconto pesam mais, depois avaliação e comissão."""
    return round(
        (oferta["desconto"] or 0) * 0.8
        + ((oferta["nota"] or 4.5) - 4.0) * 20
        + math.log10(max(oferta["vendas"] or (oferta.get("avaliacoes") or 0) * 10 or 1, 1)) * 8
        + (oferta["comissao_taxa"] or 0) * 100 * 0.5
        + (5 if oferta["loja_oficial"] else 0),
        1,
    )


def misturar_categorias(ofertas):
    """Intercala as categorias (a melhor de cada, depois a segunda de cada...) para a vitrine não ficar só com um nicho."""
    por_categoria = {}
    for oferta in ofertas:
        por_categoria.setdefault(oferta["categoria"], []).append(oferta)
    filas = list(por_categoria.values())
    mistura = []
    while any(filas):
        for fila in filas:
            if fila:
                mistura.append(fila.pop(0))
    return mistura


def escolher(nos, hist):
    """Recebe os produtos crus das lojas e devolve todas as ofertas aprovadas, da melhor para a pior, já registrando os preços."""
    vistos = {}
    nomes = set()
    for no in nos:
        oferta = normalizar(no)
        parecido = " ".join(oferta["nome"].lower().split()[:5])  # o mesmo produto em lojas diferentes
        if oferta["chave"] in vistos or parecido in nomes or not oferta["preco"]:
            continue
        vistos[oferta["chave"]] = oferta
        nomes.add(parecido)

    aprovadas = []
    for oferta in vistos.values():
        item = historico.registrar_preco(hist, oferta["chave"], oferta["nome"], oferta["preco"])
        if motivo_reprovacao(oferta):
            continue
        if historico.enviado_recentemente(item, config.DIAS_SEM_REPETIR):
            continue
        menor = historico.menor_preco(item)
        oferta["menor_preco_visto"] = menor
        oferta["preco_conferido"] = menor is not None
        if menor is not None and oferta["preco"] > menor * config.TOLERANCIA_MENOR_PRECO:
            continue  # já esteve mais barato: o desconto não é real agora
        oferta["pontos"] = pontuar(oferta)
        aprovadas.append(oferta)

    aprovadas.sort(key=lambda o: o["pontos"], reverse=True)
    # O mesmo produto em lojas diferentes (ou já mandado nos últimos dias) aparece uma vez só: fica o de mais pontos.
    return semelhanca.sem_repetidos(aprovadas, historico.nomes_enviados(hist, config.DIAS_SEM_REPETIR))
