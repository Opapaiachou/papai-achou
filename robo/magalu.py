"""Busca ofertas na loja do Papai Achou no Magalu (Influenciador Magalu).

O link de afiliado do Magalu é o próprio endereço do produto dentro da loja do divulgador
(magazinevoce.com.br/magazineopapaiachou/...). A página de busca da loja traz os produtos
com preço, preço "de", preço no Pix, nota e número de avaliações, então o robô consegue
buscar e montar as ofertas sozinho, sem planilha.
"""

import json
import re
import time

import requests

from robo import config

BASE = "https://www.magazinevoce.com.br"
CABECALHOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def _num(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _produtos_da_pagina(html):
    achado = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not achado:
        return []
    dados = json.loads(achado.group(1))
    try:
        return dados["props"]["pageProps"]["data"]["search"]["products"] or []
    except (KeyError, TypeError):
        return []


def converter(produto, categoria):
    """Produto do Magalu -> mesmo formato que o robô usa para a Shopee."""
    preco_info = produto.get("price") or {}
    de = _num(preco_info.get("price"))                       # preço "de"
    por = _num(preco_info.get("bestPrice")) or _num(preco_info.get("fullPrice"))
    if not por:
        return None
    desconto = round((1 - por / de) * 100) if de and de > por else None
    nota = (produto.get("rating") or {}).get("score")
    avaliacoes = (produto.get("rating") or {}).get("count")
    foto = (produto.get("image") or "").replace("{w}x{h}", "618x463")
    caminho = produto.get("path") or produto.get("url") or ""
    return {
        "itemId": produto.get("id"),
        "shopId": "magalu",
        "productName": produto.get("title") or "",
        "priceMin": por,
        "priceDiscountRate": desconto,
        "_precoAntigo": de if de and de > por else None,
        "_formaPreco": preco_info.get("paymentMethodDescription") or "",
        "ratingStar": nota,
        "sales": None,                       # o Magalu não informa unidades vendidas
        "_avaliacoes": avaliacoes,
        "commissionRate": None,              # comissão do Magalu depende da categoria (até 12%)
        "commission": None,
        "imageUrl": foto,
        "productLink": BASE + caminho,
        "offerLink": BASE + caminho,         # já é o link da loja do divulgador
        "shopName": "Magalu",
        "shopType": [],
        "_categoria": categoria,
        "_plataforma": "Magalu",
        "_disponivel": produto.get("available", True),
    }


def buscar(palavra, categoria, sessao=None):
    sessao = sessao or requests.Session()
    url = f"{BASE}/{config.MAGALU_LOJA}/busca/{requests.utils.quote(palavra)}/"
    resposta = sessao.get(url, headers=CABECALHOS, timeout=30)
    resposta.raise_for_status()
    nos = []
    for produto in _produtos_da_pagina(resposta.text):
        no = converter(produto, categoria)
        if no and no["_disponivel"]:
            nos.append(no)
    return nos


def coletar():
    sessao = requests.Session()
    nos, falhas = [], 0
    for palavra, categoria in config.PALAVRAS_CHAVE.items():
        try:
            achados = buscar(palavra, categoria, sessao)
            nos += achados
        except Exception as erro:  # uma palavra com problema não derruba a rodada
            falhas += 1
            print(f"Aviso Magalu: falha ao buscar '{palavra}': {erro}")
        time.sleep(config.MAGALU_PAUSA)
    print(f"Magalu: {len(nos)} produtos lidos em {len(config.PALAVRAS_CHAVE)} buscas ({falhas} falhas).")
    return nos


if __name__ == "__main__":
    # Teste rápido: python -m robo.magalu
    teste = buscar("garrafa termica", "Casa e cozinha")
    print(f"{len(teste)} produtos")
    for no in teste[:5]:
        print(no["productName"][:60], "|", no["priceMin"], "| de", no["_precoAntigo"], "|", no["ratingStar"],
              f"({no['_avaliacoes']})", "|", no["offerLink"])
