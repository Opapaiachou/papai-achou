"""Ofertas da Shopee pelo feed de produtos do painel de afiliados (Shopee Afiliados > Feed de produtos).

O link de download do feed tem a sua identificação, então ele fica guardado como segredo
SHOPEE_FEED_URL no GitHub (o repositório é público). O robô:
- baixa o feed para um arquivo temporário (pode ter centenas de milhares de produtos);
- reconhece o formato sozinho (CSV com vírgula, ponto e vírgula ou tab; compactado em gzip ou zip);
- acha as colunas pelo nome (a Shopee muda os nomes de vez em quando) e mostra no log o que achou;
- fica só com o que cabe no nicho, tem desconto de verdade e boa nota, e entrega no mesmo
  formato das outras lojas (a curadoria faz o resto).
"""

import csv
import gzip
import io
import os
import re
import tempfile
import zipfile

import requests

from robo import awin, config, regras

# Nome da coluna no feed -> campo do robô. A primeira que existir vale.
CANDIDATOS = {
    "item": ("itemid", "item_id", "item id", "product_id", "productid", "id"),
    "loja_id": ("shopid", "shop_id", "shop id"),
    "nome": ("title", "product_name", "productname", "name", "item_name", "product name"),
    "preco": ("sale_price", "price_after_discount", "discounted_price", "final_price", "current_price",
              "sale price", "pricemin", "price_min"),
    "de": ("price", "original_price", "price_before_discount", "regular_price", "price_max", "pricemax"),
    "desconto": ("discount_percentage", "discount", "discount_rate", "pricediscountrate", "discount percentage"),
    "foto": ("image_link", "image_url", "imageurl", "image", "main_image", "image link"),
    "link": ("product_short link", "product_short_link", "product short link", "short_link", "shortlink",
             "offer_link", "offerlink", "affiliate_link", "affiliate link", "product_link", "productlink", "link"),
    "nota": ("item_rating", "rating", "ratingstar", "rating_star", "item rating"),
    "vendas": ("item_sold", "sold", "sales", "historical_sold", "item sold"),
    "loja": ("shop_name", "shopname", "shop name"),
    "comissao": ("commission_rate", "commissionrate", "commission rate", "seller_commission_rate"),
    "estoque": ("stock", "availability"),
    "categorias": ("global_category1", "global_category2", "global_category3", "category", "category_name",
                   "global_category", "categories"),
}
# Quantos produtos da Shopee entregar para a curadoria, no máximo, e quantos por categoria.
MAXIMO = 400
POR_CATEGORIA = 60


def _chave(nome):
    return re.sub(r"\s+", " ", (nome or "").strip().lower())


def _mapear(cabecalho):
    """Descobre qual coluna do feed é cada informação."""
    colunas = {_chave(c): c for c in cabecalho if c}
    mapa = {}
    for campo, opcoes in CANDIDATOS.items():
        achadas = [colunas[o] for o in opcoes if o in colunas]
        if campo == "categorias":
            mapa[campo] = achadas
        elif achadas:
            mapa[campo] = achadas[0]
    return mapa


def _num(valor):
    if valor in (None, ""):
        return None
    texto = str(valor).replace("%", "").strip()
    return awin._num(texto)


def _baixar(url):
    """Baixa o feed para um arquivo temporário e devolve um leitor de texto já descompactado."""
    temporario = tempfile.NamedTemporaryFile(delete=False, suffix=".feed")
    with requests.get(url, stream=True, timeout=600, headers={"User-Agent": "Mozilla/5.0"}) as resposta:
        resposta.raise_for_status()
        print(f"Shopee feed: tipo {resposta.headers.get('content-type')}")
        for pedaco in resposta.iter_content(chunk_size=1 << 20):
            temporario.write(pedaco)
    temporario.close()
    tamanho = os.path.getsize(temporario.name)
    with open(temporario.name, "rb") as f:
        inicio = f.read(4)
    print(f"Shopee feed: {tamanho / 1e6:.1f} MB baixados")
    if inicio[:2] == b"\x1f\x8b":
        bruto = gzip.open(temporario.name, "rb")
    elif inicio[:2] == b"PK":
        pacote = zipfile.ZipFile(temporario.name)
        arquivos = [n for n in pacote.namelist() if not n.endswith("/")]
        print(f"Shopee feed: zip com {arquivos[:5]}")
        bruto = pacote.open(arquivos[0])
    else:
        bruto = open(temporario.name, "rb")
    return io.TextIOWrapper(bruto, encoding="utf-8-sig", errors="replace", newline="")


def converter(linha, mapa):
    """Linha do feed -> mesmo formato que o robô usa para as outras lojas. None se não serve."""
    pega = lambda campo: linha.get(mapa[campo]) if campo in mapa else None
    nome = (pega("nome") or "").strip()
    link = (pega("link") or "").strip()
    if not nome or not link.startswith("http"):
        return None
    por, de = _num(pega("preco")), _num(pega("de"))
    if not por and de:
        por, de = de, None
    if not por:
        return None
    desconto = _num(pega("desconto"))
    if de and de > por:
        desconto = round((1 - por / de) * 100)
    elif desconto and 0 < desconto < 100:
        de = round(por / (1 - desconto / 100), 2)
    else:
        return None  # sem desconto informado: fica de fora
    if desconto < config.DESCONTO_MINIMO or desconto > awin.DESCONTO_MAXIMO_AWIN:
        return None
    if not config.PRECO_MINIMO <= por <= config.PRECO_MAXIMO:
        return None
    estoque = str(pega("estoque") or "").strip().lower()
    if estoque in ("0", "out of stock", "sem estoque", "esgotado"):
        return None
    nota, vendas = _num(pega("nota")), _num(pega("vendas"))
    if nota is not None and 0 < nota < config.NOTA_MINIMA:
        return None
    if vendas is not None and vendas < config.VENDAS_MINIMAS:
        return None
    if regras.motivo_bloqueio(nome):
        return None
    categorias = " ".join(linha.get(c) or "" for c in mapa.get("categorias", []))
    categoria = awin.categoria_de(nome, categorias)
    if not categoria:
        return None  # fora do nicho
    comissao = _num(pega("comissao"))
    if comissao and comissao > 1:  # veio em % (ex.: 7) e o robô usa fração (0,07)
        comissao = comissao / 100
    item = pega("item") or re.sub(r"\W", "", link)[-16:]
    return {
        "itemId": item,
        "shopId": pega("loja_id") or "shopee",
        "productName": nome,
        "priceMin": por,
        "priceDiscountRate": desconto,
        "_precoAntigo": de,
        "ratingStar": nota if nota and nota > 0 else None,
        "sales": int(vendas) if vendas is not None else None,
        "commissionRate": comissao,
        "commission": None,
        "imageUrl": pega("foto") or "",
        "productLink": link,
        "offerLink": link,
        "shopName": pega("loja") or "Shopee",
        "shopType": [],
        "_categoria": categoria,
        "_plataforma": "Shopee",
    }


def _nota_interna(no):
    """Ordem dentro de cada categoria: desconto e vendas pesam mais."""
    import math
    return (no["priceDiscountRate"] or 0) + math.log10(max(no["sales"] or 1, 1)) * 8 + ((no["ratingStar"] or 4.5) - 4) * 20


def coletar():
    url = os.environ.get("SHOPEE_FEED_URL", "").strip()
    if not url:
        print("Shopee feed fora desta rodada: ainda sem o segredo SHOPEE_FEED_URL.")
        return []
    texto = _baixar(url)
    primeira = texto.readline()
    separador = max([",", ";", "\t", "|"], key=primeira.count)
    cabecalho = next(csv.reader([primeira], delimiter=separador))
    mapa = _mapear(cabecalho)
    print(f"Shopee feed: {len(cabecalho)} colunas: {cabecalho[:40]}")
    print(f"Shopee feed: colunas usadas: {mapa}")
    faltando = [c for c in ("nome", "preco", "link") if c not in mapa]
    if faltando:
        print(f"Shopee feed: não achei as colunas {faltando}; nada entra até ajustar o robô.")
        return []
    leitor = csv.DictReader(texto, fieldnames=cabecalho, delimiter=separador)
    por_categoria, lidas, aproveitadas = {}, 0, 0
    for linha in leitor:
        lidas += 1
        if lidas <= 2:
            amostra = {k: (v or "")[:60] for k, v in linha.items() if k and v}
            print(f"Shopee feed amostra: {amostra}")
        try:
            no = converter(linha, mapa)
        except Exception:  # linha quebrada não derruba a rodada
            no = None
        if not no:
            continue
        aproveitadas += 1
        fila = por_categoria.setdefault(no["_categoria"], [])
        fila.append(no)
        if len(fila) > POR_CATEGORIA * 4:  # guarda só os melhores de cada categoria (memória)
            fila.sort(key=_nota_interna, reverse=True)
            del fila[POR_CATEGORIA:]
    nos = []
    for fila in por_categoria.values():
        fila.sort(key=_nota_interna, reverse=True)
        nos += fila[:POR_CATEGORIA]
    nos.sort(key=_nota_interna, reverse=True)
    nos = nos[:MAXIMO]
    resumo = ", ".join(f"{c} {min(len(f), POR_CATEGORIA)}" for c, f in por_categoria.items())
    print(f"Shopee feed: {lidas} produtos lidos, {aproveitadas} no nicho e com desconto; {len(nos)} vão para a curadoria ({resumo}).")
    return nos
