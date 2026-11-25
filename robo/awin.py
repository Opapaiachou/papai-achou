"""Ofertas das marcas da Awin (feed oficial de produtos).

Como funciona:
- Na Awin, cada marca aprovada pode liberar um "feed de produtos" (lista com preço, preço antigo,
  foto, estoque e o link de afiliado já pronto, o campo aw_deep_link).
- Em Ferramentas > Crie um Feed, no topo, fica o link "Download da Lista de Feed" (feedList).
  Esse link tem a sua chave, então ele fica guardado como segredo AWIN_FEED_URL no GitHub
  (o repositório é público). Com ele o robô descobre sozinho as marcas aprovadas no Brasil:
  cada marca nova aprovada entra na rodada seguinte, sem mexer em nada.
- Feed parado há mais de DIAS_FEED_MAXIMO dias fica de fora (preço velho não vai para o site).
- O robô baixa o feed, fica só com o que tem desconto de verdade, está em estoque e cabe no
  nosso nicho, e entrega no mesmo formato das outras lojas.
"""

import csv
import gzip
import io
import os
import re
import unicodedata
from datetime import datetime, timedelta

import requests

from robo import config, monitor

# Até quantos produtos de cada marca entram por rodada (para a vitrine não virar uma loja só).
POR_MARCA = 12
# Desconto mínimo para um produto da Awin entrar (as marcas não informam vendas nem nota).
DESCONTO_MINIMO_AWIN = 15
# Desconto acima disso na Awin quase sempre é "preço de" inflado pela loja (ex.: bolsa de R$ 1.599 por R$ 269).
DESCONTO_MAXIMO_AWIN = 70
# Feed que a marca não atualiza há mais que isso fica de fora (o preço pode estar velho).
DIAS_FEED_MAXIMO = 10
# Colunas pedidas à Awin para cada feed.
COLUNAS = ("aw_deep_link,product_name,aw_product_id,merchant_product_id,merchant_image_url,aw_image_url,"
           "merchant_category,category_name,search_price,store_price,rrp_price,product_price_old,in_stock,"
           "savings_percent,currency,merchant_name,merchant_id,merchant_deep_link,average_rating,reviews")

# Palavra no nome/categoria do produto -> categoria da vitrine. A primeira que bater vale.
MAPA_CATEGORIAS = [
    (("gamer", "gaming", "headset", "xbox", "playstation", "ps5", "nintendo", "console", "mousepad",
      "placa de video", "rtx", "geforce", "radeon", "memoria ram", "ssd", "teclado mecanico", "redragon",
      "hyperx", "razer"), "Gamer"),
    (("legging", "fitness", "academia", "treino", "whey", "creatina", "corrida", "running", "yoga", "haltere",
      "suplemento", "proteina", "garrafa termica stanley", "squeeze", "dri-fit", "dri fit", "drifit", "aeroswift",
      "chuteira", "futsal", "society", "ciclista", "segunda pele", "compressao", "top esportivo", "bermuda esportiva",
      "short esportivo", "shorts esportivo", "training", "treinamento", "pro sculpt", "nike pro ", "techfit",
      "aeroready", "climacool", "wave rider", "wave prophecy", "tenis de corrida", "ziclo", "pilates", "musculacao"), "Fitness"),
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


# Marcas cujo nome engana o mapa (ex.: "Lança Perfume" é roupa, não perfume): saem antes de comparar.
MARCAS_CONFUSAS = ("lanca perfume", "perfume de mulher")


def categoria_de(*textos):
    alvo = " " + " ".join(_sem_acento(t) for t in textos) + " "
    for marca in MARCAS_CONFUSAS:
        alvo = alvo.replace(marca, " ")
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
    economia = _num(linha.get("savings_percent"))
    if por and not de and economia and 0 < economia < 90:  # alguns feeds só trazem o % de desconto
        de = round(por / (1 - economia / 100), 2)
    sem_referencia = bool(por) and not de  # feed sem "preço de" (ex.: Kabum): vai para o acompanhamento
    if not por or (de and de <= por):
        return None
    if sem_referencia:
        desconto = None
        if not config.PRECO_MINIMO <= por <= config.PRECO_MAXIMO:
            return None
    else:
        desconto = round((1 - por / de) * 100)
        if desconto < DESCONTO_MINIMO_AWIN or desconto > DESCONTO_MAXIMO_AWIN:  # desconto absurdo: preço de inflado
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
        "_semReferencia": sem_referencia,
    }


def _motivo(linha):
    """Por que a linha ficou de fora (só para o diagnóstico no log)."""
    por = _num(linha.get("search_price")) or _num(linha.get("store_price"))
    de = _num(linha.get("product_price_old")) or _num(linha.get("rrp_price"))
    economia = _num(linha.get("savings_percent"))
    if not por:
        return "sem preço"
    if not de and not economia:
        return "sem preço antigo (fora do nicho ou da faixa de preço)"
    if de and de <= por:
        return "preço antigo igual ou menor"
    if not categoria_de(linha.get("product_name"), linha.get("merchant_category"), linha.get("category_name")):
        return "fora do nicho"
    return "desconto menor que o mínimo ou sem estoque"


def _ler_feed(conteudo):
    if conteudo[:2] == b"\x1f\x8b":
        conteudo = gzip.decompress(conteudo)
    texto = conteudo.decode("utf-8-sig", errors="replace")
    separador = "|" if texto.split("\n", 1)[0].count("|") > texto.split("\n", 1)[0].count(",") else ","
    return csv.DictReader(io.StringIO(texto), delimiter=separador)


def _feeds_ativos(url_lista):
    """Lê a lista de feeds e devolve os das marcas aprovadas no Brasil: (marca, url, atualizado_em)."""
    resposta = requests.get(url_lista, timeout=60)
    resposta.raise_for_status()
    feeds = []
    for linha in csv.DictReader(io.StringIO(resposta.content.decode("utf-8-sig", errors="replace"))):
        if (linha.get("Membership Status") or "").strip().lower() != "active":
            continue
        if (linha.get("Primary Region") or "").strip().upper() != "BR":
            continue
        url = (linha.get("URL") or "").strip()
        if "productdata.awin.com" not in url:
            print(f"Awin: feed de {linha.get('Advertiser Name')} em formato que o robô ainda não lê; ficou de fora.")
            continue
        url = re.sub(r"/columns/[^/]+/", "/columns/" + COLUNAS.replace(",", "%2C") + "/", url)
        try:
            atualizado = datetime.strptime((linha.get("Last Imported") or "").strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            atualizado = None
        feeds.append(((linha.get("Advertiser Name") or "").replace(" BR", "").strip(), url, atualizado))
    return feeds


def _baixar(url):
    resposta = requests.get(url, timeout=180)
    resposta.raise_for_status()
    return list(_ler_feed(resposta.content))


def coletar():
    url = os.environ.get("AWIN_FEED_URL", "").strip()
    if not url:
        print("Awin fora desta rodada: ainda sem o segredo AWIN_FEED_URL (lista de feeds).")
        return []
    if "feedList" in url:
        linhas, limite = [], datetime.now() - timedelta(days=DIAS_FEED_MAXIMO)
        for marca, url_feed, atualizado in _feeds_ativos(url):
            if atualizado and atualizado < limite:
                print(f"Awin: {marca} fora (feed sem atualização desde {atualizado:%d/%m/%Y}).")
                continue
            try:
                novas = _baixar(url_feed)
                print(f"Awin: {marca} com {len(novas)} produtos no feed.")
                linhas += novas
            except Exception as erro:  # uma marca com problema não derruba as outras
                print(f"Aviso Awin: falha no feed de {marca}: {erro}")
    else:
        linhas = _baixar(url)
    por_marca, motivos = {}, {}
    acompanhados, em_queda = 0, 0
    precos = monitor.carregar()
    for linha in linhas:
        no = converter(linha)
        if no and no.get("_semReferencia"):
            # Sem "preço de" no feed: anota o preço e só vira oferta se caiu frente ao nosso histórico.
            acompanhados += 1
            chave = f"awin-{no['shopId']}-{no['itemId']}"
            tipico = monitor.registrar(precos, chave, no["productName"], no["priceMin"])
            desconto = monitor.em_queda(no["priceMin"], tipico)
            if not desconto:
                continue
            em_queda += 1
            no["_precoAntigo"] = round(tipico, 2)
            no["priceDiscountRate"] = desconto
        if no:
            por_marca.setdefault(no["shopName"], []).append(no)
        else:
            marca = (linha.get("merchant_name") or "?").replace(" BR", "").strip()
            chave = (marca, _motivo(linha))
            motivos[chave] = motivos.get(chave, 0) + 1
    for (marca, motivo), qtd in sorted(motivos.items(), key=lambda x: -x[1])[:12]:
        print(f"Awin diagnóstico: {marca} - {qtd} fora por {motivo}")
    for marca, lista in por_marca.items():
        for no in lista[:3]:
            print(f"Awin exemplo: {marca} | {no['productName'][:50]} | R$ {no['priceMin']} de {no['_precoAntigo']} | {no['_categoria']}")
    nos = []
    for marca, lista in por_marca.items():
        lista.sort(key=lambda n: n["priceDiscountRate"], reverse=True)
        nos += lista[:POR_MARCA]
    monitor.salvar(precos)
    if acompanhados:
        print(f"Awin acompanhamento: {acompanhados} produtos sem 'preço de' com preço anotado, {em_queda} em queda real hoje.")
    print(f"Awin: {len(linhas)} produtos lidos, {len(nos)} no nicho e com desconto, de {len(por_marca)} marcas.")
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
