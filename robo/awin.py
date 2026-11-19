"""Ofertas das marcas da Awin (feed oficial de produtos).

Como funciona:
- Na Awin, cada marca aprovada pode liberar um "feed de produtos" (lista com preço, preço antigo,
  foto, estoque e o link de afiliado já pronto, o campo aw_deep_link).
- Em Ferramentas > Crie um Feed você escolhe as marcas e a Awin gera UM endereço de download.
  Esse endereço tem a sua chave, então ele fica guardado como segredo AWIN_FEED_URL no GitHub
  (o repositório é público).
- O robô baixa o feed, fica só com o que tem desconto de verdade, está em estoque e cabe no
  nosso nicho, e entrega no mesmo formato das outras lojas.
"""

import csv
import gzip
import io
import os
import unicodedata

import requests

# Até quantos produtos de cada marca entram por rodada (para a vitrine não virar uma loja só).
POR_MARCA = 12
# Desconto mínimo para um produto da Awin entrar (as marcas não informam vendas nem nota).
DESCONTO_MINIMO_AWIN = 15

# Palavra no nome/categoria do produto -> categoria da vitrine. A primeira que bater vale.
MAPA_CATEGORIAS = [
    (("legging", "fitness", "academia", "treino", "whey", "creatina", "corrida", "running", "yoga", "haltere",
      "suplemento", "proteina", "garrafa termica stanley", "squeeze"), "Fitness"),
    (("mochila escolar", "estojo", "lancheira", "caderno", "escolar"), "Escola"),
    (("infantil", "bebe", "kids", "brinquedo", "lego", "crianca", "menino", "menina"), "Crianças"),
    (("perfume", "maquiagem", "batom", "base ", "skincare", "hidratante", "shampoo", "condicionador",
      "creme", "serum", "colonia", "desodorante", "esmalte", "rimel", "mascara de cilios"), "Maquiagem e beleza"),
    (("fone", "carregador", "smartwatch", "relogio inteligente", "caixa de som", "bluetooth", "celular",
      "notebook", "tablet", "mouse", "teclado", "smart tv", "monitor", "camera"), "Tecnologia útil"),
    (("panela", "air fryer", "fritadeira", "liquidificador", "cafeteira", "aspirador", "jogo de cama",
      "toalha", "lencol", "travesseiro", "pote", "copo", "garrafa", "cozinha", "organizador", "edredom",
      "ventilador", "geladeira", "micro-ondas", "microondas", "fogao", "sofa", "colchao"), "Casa e cozinha"),
    (("tenis", "camiseta", "vestido", "calca", "bolsa", "relogio", "oculos", "sandalia", "chinelo", "jaqueta",
      "blusa", "bermuda", "short", "saia", "camisa", "sapato", "bota", "mala", "mochila"), "Moda"),
]


def _sem_acento(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def categoria_de(*textos):
    alvo = " " + " ".join(_sem_acento(t) for t in textos) + " "
    for palavras, categoria in MAPA_CATEGORIAS:
        if any(p in alvo for p in palavras):
            return categoria
    return None  # fora do nicho: fica de fora


def _num(valor):
    if valor in (None, ""):
        return None
    texto = str(valor).strip().replace("R$", "").replace("BRL", "").strip()
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def converter(linha):
    """Linha do feed da Awin -> mesmo formato que o robô usa para as outras lojas."""
    por = _num(linha.get("search_price")) or _num(linha.get("store_price"))
    de = _num(linha.get("product_price_old")) or _num(linha.get("rrp_price"))
    if not por or not de or de <= por:
        return None
    desconto = round((1 - por / de) * 100)
    if desconto < DESCONTO_MINIMO_AWIN or desconto > 85:  # desconto absurdo costuma ser erro do feed
        return None
    estoque = str(linha.get("in_stock", "1")).strip().lower()
    if estoque in ("0", "false", "no", "nao", "não"):
        return None
    if (linha.get("currency") or "BRL").upper() != "BRL":
        return None
    nome = (linha.get("product_name") or "").strip()
    categoria = categoria_de(nome, linha.get("merchant_category"), linha.get("category_name"))
    if not categoria or not linha.get("aw_deep_link"):
        return None
    marca = (linha.get("merchant_name") or "").replace(" BR", "").strip()
    nota = _num(linha.get("average_rating"))
    avaliacoes = _num(linha.get("reviews"))
    return {
        "itemId": linha.get("aw_product_id") or linha.get("merchant_product_id"),
        "shopId": linha.get("merchant_id") or "awin",
        "productName": nome,
        "priceMin": por,
        "priceDiscountRate": desconto,
        "_precoAntigo": de,
        "_formaPreco": "",
        "ratingStar": nota if nota and 0 < nota <= 5 else None,
        "sales": None,
        "_avaliacoes": int(avaliacoes) if avaliacoes else None,
        "commissionRate": None,
        "commission": None,
        "imageUrl": linha.get("merchant_image_url") or linha.get("aw_image_url") or "",
        "productLink": linha.get("merchant_deep_link") or "",
        "offerLink": linha.get("aw_deep_link"),       # link de afiliado já rastreado pela Awin
        "shopName": marca,
        "shopType": [1],                              # marca oficial (loja da própria marca)
        "_categoria": categoria,
        "_plataforma": "Awin",
    }


def _ler_feed(conteudo):
    if conteudo[:2] == b"\x1f\x8b":
        conteudo = gzip.decompress(conteudo)
    texto = conteudo.decode("utf-8-sig", errors="replace")
    separador = "|" if texto.split("\n", 1)[0].count("|") > texto.split("\n", 1)[0].count(",") else ","
    return csv.DictReader(io.StringIO(texto), delimiter=separador)


def coletar():
    url = os.environ.get("AWIN_FEED_URL", "").strip()
    if not url:
        print("Awin fora desta rodada: ainda sem o segredo AWIN_FEED_URL (feed de produtos).")
        return []
    resposta = requests.get(url, timeout=180)
    resposta.raise_for_status()
    por_marca, lidos = {}, 0
    for linha in _ler_feed(resposta.content):
        lidos += 1
        no = converter(linha)
        if no:
            por_marca.setdefault(no["shopName"], []).append(no)
    nos = []
    for marca, lista in por_marca.items():
        lista.sort(key=lambda n: n["priceDiscountRate"], reverse=True)
        nos += lista[:POR_MARCA]
    print(f"Awin: {lidos} produtos no feed, {len(nos)} no nicho e com desconto, de {len(por_marca)} marcas.")
    return nos


if __name__ == "__main__":
    # Teste rápido com um arquivo baixado: python -m robo.awin caminho/feed.csv
    import sys
    with open(sys.argv[1], "rb") as f:
        linhas = list(_ler_feed(f.read()))
    convertidos = [n for n in (converter(l) for l in linhas) if n]
    print(f"{len(linhas)} linhas, {len(convertidos)} aproveitadas")
    for n in convertidos[:8]:
        print(n["shopName"], "|", n["productName"][:50], "|", n["priceMin"], "de", n["_precoAntigo"], "|", n["_categoria"])
