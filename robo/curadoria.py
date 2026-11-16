"""Filtra e pontua as ofertas segundo o checklist do playbook do Papai Achou."""

import math

from robo import config, historico, regras


def _num(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _loja_oficial(tipo):
    """shopType vem como lista de códigos; 1 = loja oficial (Shopee Mall)."""
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return any(str(t) == "1" for t in tipos)


def normalizar(no):
    """Converte o produto da Shopee para um formato simples, com números de verdade."""
    preco = _num(no.get("priceMin"))
    desconto = _num(no.get("priceDiscountRate"))
    preco_antigo = round(preco / (1 - desconto / 100), 2) if 0 < desconto < 100 else None
    return {
        "chave": f"{no.get('shopId')}-{no.get('itemId')}",
        "nome": (no.get("productName") or "").strip(),
        "preco": preco,
        "preco_antigo": preco_antigo,
        "desconto": desconto,
        "nota": _num(no.get("ratingStar")),
        "vendas": int(_num(no.get("sales"))),
        "comissao_taxa": _num(no.get("commissionRate")),
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
    if oferta["nota"] < config.NOTA_MINIMA:
        return "nota baixa"
    if oferta["vendas"] < config.VENDAS_MINIMAS:
        return "poucas vendas"
    if oferta["desconto"] < config.DESCONTO_MINIMO:
        return "desconto pequeno"
    if oferta["comissao_taxa"] < config.COMISSAO_MINIMA:
        return "comissão baixa"
    if not config.PRECO_MINIMO <= oferta["preco"] <= config.PRECO_MAXIMO:
        return "fora da faixa de preço"
    if not oferta["link"] or not oferta["foto"]:
        return "sem link ou foto"
    return None


def pontuar(oferta):
    """Nota de 0 a ~100: vendas e desconto pesam mais, depois avaliação e comissão."""
    return round(
        oferta["desconto"] * 0.8
        + (oferta["nota"] - 4.0) * 20
        + math.log10(max(oferta["vendas"], 1)) * 8
        + oferta["comissao_taxa"] * 100 * 0.5
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
    """Recebe os produtos crus da Shopee e devolve todas as ofertas aprovadas, da melhor para a pior, já registrando os preços."""
    vistos = {}
    for no in nos:
        oferta = normalizar(no)
        if oferta["chave"] in vistos or not oferta["preco"]:
            continue
        vistos[oferta["chave"]] = oferta

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
    return aprovadas
