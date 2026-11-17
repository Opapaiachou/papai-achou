"""Lê as planilhas de links que a Shopee gera em "Oferta de produto › Obter Link".

Enquanto a Open API não é liberada, o robô funciona assim: você marca os produtos no
painel de afiliados, baixa a planilha (CSV) e sobe na pasta "entrada" do repositório.
O robô lê, filtra pelas mesmas regras, manda as melhores para o seu Telegram e
atualiza a vitrine. Depois move a planilha para "entrada/processadas".

Os nomes das colunas variam (português ou inglês), então a leitura procura por apelidos.
"""

import csv
import glob
import io
import os
import re
import shutil
import unicodedata

from robo import config

PASTA = os.path.dirname(os.path.dirname(__file__))
ENTRADA = os.path.join(PASTA, "entrada")
PROCESSADAS = os.path.join(ENTRADA, "processadas")
FOTO_PADRAO = "https://opapaiachou.com.br/img/mascote.png"

# campo do robô -> apelidos possíveis do cabeçalho (sem acento, minúsculo)
COLUNAS = {
    "productName": ["item name", "product name", "nome do produto", "nome do item", "produto", "nome", "titulo"],
    "offerLink": ["offer link", "link da oferta", "link de oferta", "link de afiliado", "link afiliado", "short link", "link curto"],
    "productLink": ["product link", "item link", "link do produto", "link do item", "url do produto", "url"],
    "priceMin": ["price", "preco", "preco atual", "preco promocional", "preco final", "valor"],
    "precoAntigo": ["original price", "preco original", "preco antigo", "preco cheio"],
    "priceDiscountRate": ["discount", "desconto", "discount rate", "taxa de desconto"],
    "sales": ["sales", "sold", "vendas", "vendidos", "quantidade vendida"],
    "commissionRate": ["commission rate", "taxa de comissao", "comissao (%)", "% comissao"],
    "commission": ["commission", "comissao", "comissao estimada", "valor da comissao"],
    "ratingStar": ["rating", "avaliacao", "nota", "estrelas"],
    "imageUrl": ["image", "image link", "imagem", "foto", "image url", "link da imagem"],
    "shopName": ["shop name", "nome da loja", "loja", "vendedor"],
    "itemId": ["item id", "id do item", "id do produto", "product id", "itemid"],
    "shopId": ["shop id", "id da loja", "shopid"],
}

# Para descobrir a categoria pelo nome do produto (além das palavras do config).
TERMOS_CATEGORIA = {
    "Fitness": ["fitness", "academia", "treino", "legging", "whey", "creatina", "proteina", "halter", "yoga",
                "corrida", "coqueteleira", "elastico", "pre treino", "top esportivo", "esportiv"],
    "Maquiagem e beleza": ["maquiagem", "batom", "base ", "sombra", "pincel", "skincare", "serum", "perfume",
                           "hidratante", "mascara de cilios", "cabelo", "shampoo", "creme", "esmalte", "beleza"],
    "Moda": ["vestido", "blusa", "cropped", "camiseta", "calca", "short", "saia", "bolsa", "tenis", "sandalia",
             "chinelo", "relogio", "jaqueta", "moletom", "conjunto", "biquini", "cueca", "calcinha", "meia"],
    "Escola": ["escolar", "mochila", "lancheira", "caderno", "estojo", "caneta", "lapis"],
    "Crianças": ["infantil", "bebe", "brinquedo", "crianca", "boneca", "carrinho", "montessori"],
    "Casa e cozinha": ["cozinha", "organizador", "pote", "garrafa", "copo", "termic", "panela", "airfryer",
                       "air fryer", "mop", "limpeza", "toalha", "lencol", "jogo de cama", "tapete", "parafusadeira",
                       "ferramenta", "furadeira", "caneca", "omeleteira", "espelho", "lavabo", "banheiro",
                       "eletrica", "eletrico", "liquidificador", "cafeteira", "sanduicheira"],
    "Tecnologia útil": ["fone", "carregador", "cabo usb", "bluetooth", "smartwatch", "celular", "caixa de som",
                        "mouse", "teclado", "capinha de celular", "capinha celular", "pelicula", "power bank"],
}


def _limpo(texto):
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto).strip()


def _numero(valor):
    """'R$ 1.299,90' -> 1299.9 · '28%' -> 28 · '1mil+' -> 1000 · '4,8' -> 4.8"""
    if valor is None:
        return None
    texto = _limpo(valor).replace("r$", "").replace("%", "").replace("+", "").strip()
    if not texto:
        return None
    multiplicador = 1
    if "mil" in texto or texto.endswith("k"):
        multiplicador = 1000
        texto = texto.replace("mil", "").replace("k", "").strip()
    texto = re.sub(r"[^0-9,.\-]", "", texto)
    if not texto:
        return None
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1:
        texto = texto.replace(".", "")
    try:
        return float(texto) * multiplicador
    except ValueError:
        return None


def _mapear_cabecalho(cabecalho):
    """Liga cada coluna da planilha a um campo do robô, pelo apelido mais específico."""
    limpos = [_limpo(c) for c in cabecalho]
    mapa = {}
    usados = set()
    # apelidos mais longos primeiro, para "preco original" não cair em "preco"
    pares = sorted(((campo, apelido) for campo, apelidos in COLUNAS.items() for apelido in apelidos),
                   key=lambda par: -len(par[1]))
    for campo, apelido in pares:
        if campo in mapa:
            continue
        for i, nome in enumerate(limpos):
            if i in usados:
                continue
            if nome == apelido or (len(apelido) > 4 and apelido in nome):
                mapa[campo] = i
                usados.add(i)
                break
    return mapa


def categoria_do_nome(nome):
    texto = _limpo(nome)
    for palavra, categoria in config.PALAVRAS_CHAVE.items():
        if _limpo(palavra) in texto:
            return categoria
    for categoria, termos in TERMOS_CATEGORIA.items():
        if any(termo in texto for termo in termos):
            return categoria
    return "Presentes"


def _ler_texto(caminho):
    with open(caminho, "rb") as f:
        bruto = f.read()
    for codificacao in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return bruto.decode("utf-8", errors="ignore")


def ler_arquivo(caminho):
    texto = _ler_texto(caminho)
    try:
        dialeto = csv.Sniffer().sniff(texto[:4000], delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
    linhas = list(csv.reader(io.StringIO(texto), dialeto))
    if not linhas:
        return []
    mapa = _mapear_cabecalho(linhas[0])
    if "offerLink" not in mapa and "productLink" not in mapa:
        print(f"Aviso: {os.path.basename(caminho)} não tem coluna de link; colunas: {linhas[0]}")
        return []

    nos = []
    for numero, linha in enumerate(linhas[1:], 2):
        def valor(campo):
            i = mapa.get(campo)
            return linha[i].strip() if i is not None and i < len(linha) else None

        nome = valor("productName") or ""
        link = valor("offerLink") or valor("productLink")
        if not nome or not link:
            continue
        preco = _numero(valor("priceMin"))
        antigo = _numero(valor("precoAntigo"))
        desconto = _numero(valor("priceDiscountRate"))
        if desconto is None and preco and antigo and antigo > preco:
            desconto = round((1 - preco / antigo) * 100)
        taxa = _numero(valor("commissionRate"))
        if taxa is not None and taxa > 1:
            taxa = taxa / 100  # 28 -> 0.28
        ids = re.findall(r"i\.(\d+)\.(\d+)", valor("productLink") or "")
        nos.append({
            "itemId": valor("itemId") or (ids[0][1] if ids else f"{os.path.basename(caminho)}-{numero}"),
            "shopId": valor("shopId") or (ids[0][0] if ids else "planilha"),
            "productName": nome,
            "priceMin": preco,
            "priceDiscountRate": desconto,
            "_precoAntigo": antigo,
            "ratingStar": _numero(valor("ratingStar")),
            "sales": _numero(valor("sales")),
            "commissionRate": taxa,
            "commission": _numero(valor("commission")),
            "imageUrl": valor("imageUrl") or FOTO_PADRAO,
            "productLink": valor("productLink"),
            "offerLink": link,
            "shopName": valor("shopName") or "Shopee",
            "shopType": [],
            "_categoria": categoria_do_nome(nome),
            "_origem": "planilha",
        })
    return nos


def arquivos_pendentes():
    return sorted(glob.glob(os.path.join(ENTRADA, "*.csv")))


def coletar():
    nos = []
    for caminho in arquivos_pendentes():
        lidos = ler_arquivo(caminho)
        print(f"{os.path.basename(caminho)}: {len(lidos)} produtos lidos.")
        nos += lidos
    return nos


def arquivar():
    os.makedirs(PROCESSADAS, exist_ok=True)
    for caminho in arquivos_pendentes():
        shutil.move(caminho, os.path.join(PROCESSADAS, os.path.basename(caminho)))
