"""Semana da Black Friday: carrosséis de ofertas (Instagram) e vídeos promocionais (TikTok)
com produtos reais do site. Tudo leva para o site (link na bio).

Uso: python semana.py            -> gera tudo da lista LOTE
     python semana.py 24-11      -> gera só o dia 24/11
No GitHub Actions, roda pelo lote3.py sem argumentos (o workflow do estúdio).
"""
import json, os, re, sys, io, urllib.request
from datetime import date
from PIL import Image, ImageDraw
import motor as m
import motor2 as m2
import posts as p
from motor2 import (Pop, Desliza, Carimbo, Risco, Toque, Apertar, palavras, gancho_kicker, carimbo,
                    numero_grande, W, H, LIMAO, VIOLETA, LILAS, AZUL, BRANCO, VERMELHO)

AQUI = os.path.dirname(os.path.abspath(__file__))
OFERTAS = os.path.join(AQUI, "..", "docs", "ofertas.json")
SAIDA = os.path.join(AQUI, "saida")      # carrosséis: saida/post_semana-DD-11 -> midia/posts
SAIDA_V = os.path.join(AQUI, "saida3")  # vídeos: saida3/tiktok-DD-11.mp4 -> midia/videos
HOJE = date.today().strftime("%d/%m")
CINZA = (120, 110, 160)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


# ---------------- dados ----------------
def moeda(v):
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


_fotos = {}


def foto(url):
    if url in _fotos:
        return _fotos[url]
    img = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            img = Image.open(io.BytesIO(r.read())).convert("RGBA")
    except Exception as e:
        print("sem foto:", url[:80], e)
    _fotos[url] = img
    return img


USADOS = set()
GENERICOS = {"kit", "jogo", "conjunto", "de", "do", "da", "com", "par", "combo", "c/", "novo", "nova", "original"}


def tipo(nome):
    """Tipo do produto (potes, garrafa, headset...) para não repetir o mesmo tipo no mesmo lote."""
    for w in nome.lower().split():
        if w not in GENERICOS and not re.search(r"\d", w):
            return w.rstrip("s")
    return nome.lower()


def escolher(qtd, categorias=None, termos=None, preco_max=None, min_desc=20):
    """Melhores ofertas com foto, intercalando as lojas, sem repetir produto."""
    ofs = json.load(open(OFERTAS, encoding="utf-8"))
    cands = []
    for o in ofs:
        if not (o.get("foto") and o.get("preco") and o.get("preco_antigo")):
            continue
        if (o.get("desconto") or 0) < min_desc or o["chave"] in USADOS:
            continue
        if categorias and o.get("categoria") not in categorias:
            continue
        if termos and not re.search(termos, o["nome"], re.I):
            continue
        if preco_max and o["preco"] > preco_max:
            continue
        cands.append(o)
    cands.sort(key=lambda o: -(o.get("desconto") or 0))
    grupos = {}
    for o in cands:
        grupos.setdefault(o["plataforma"], []).append(o)
    ordem = sorted(grupos, key=lambda k: -grupos[k][0]["desconto"])
    escolhidos, nomes = [], set()
    while len(escolhidos) < qtd and any(grupos.values()):
        for k in ordem:
            if not grupos[k] or len(escolhidos) >= qtd:
                continue
            o = grupos[k].pop(0)
            base = tipo(o["nome"])
            if base in nomes or foto(o["foto"]) is None:
                continue
            nomes.add(base)
            escolhidos.append(o)
    for o in escolhidos:
        USADOS.add(o["chave"])
    return escolhidos


# ---------------- extenso (para a voz) ----------------
_U = "zero um dois três quatro cinco seis sete oito nove dez onze doze treze quatorze quinze dezesseis dezessete dezoito dezenove".split()
_D = "_ _ vinte trinta quarenta cinquenta sessenta setenta oitenta noventa".split()
_C = "_ cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos".split()


def extenso(n):
    n = int(n)
    if n < 20:
        return _U[n]
    if n < 100:
        return _D[n // 10] + ("" if n % 10 == 0 else " e " + _U[n % 10])
    if n == 100:
        return "cem"
    if n < 1000:
        return _C[n // 100] + ("" if n % 100 == 0 else " e " + extenso(n % 100))
    mil = "mil" if n // 1000 == 1 else extenso(n // 1000) + " mil"
    resto = n % 1000
    if not resto:
        return mil
    return mil + (" e " if resto < 100 or resto % 100 == 0 else " ") + extenso(resto)


def reais(v):
    return extenso(round(v)) + " reais"


def nome_falado(nome):
    pal = [w for w in re.sub(r"[^\wÀ-ú ]", " ", nome).split() if not re.search(r"\d", w)][:4]
    while pal and pal[-1].lower() in ("de", "da", "do", "para", "com", "e", "em", "sem", "kit", "jogo"):
        pal.pop()
    return " ".join(pal).lower()


# ---------------- sprites de produto ----------------
def foto_quadro(o, larg, alt, raio=34):
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, larg - 1, alt - 1), radius=raio, fill=BRANCO)
    f = foto(o["foto"])
    if f is not None:
        f = f.copy()
        f.thumbnail((larg - 60, alt - 60), Image.LANCZOS)
        img.alpha_composite(f, ((larg - f.width) // 2, (alt - f.height) // 2))
    return img


def selo_desconto(desc, d=210):
    img = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.ellipse((0, 0, d - 1, d - 1), fill=LIMAO, outline=AZUL, width=6)
    f1, f2 = m.fonte(int(d * .34), "Black"), m.fonte(int(d * .16), "Black")
    t1 = f"-{int(round(desc))}%"
    g.text(((d - f1.getlength(t1)) / 2, d * .22), t1, font=f1, fill=AZUL)
    g.text(((d - f2.getlength("OFF")) / 2, d * .6), "OFF", font=f2, fill=AZUL)
    return img.rotate(10, resample=Image.BICUBIC, expand=True)


def nome_curto(nome, tam, larg, linhas=2):
    """Corta o nome para caber em no máximo 2 linhas."""
    f = m.fonte(tam, "Bold")
    out = ""
    for w in nome.replace("*", "").split():
        t = (out + " " + w).strip()
        if len(m.quebrar(t + "…", f, larg)) > linhas:
            return out.rstrip(",;-– ") + "…"
        out = t
    return out


def bloco_preco(o, larg=900, claro=False):
    """Nome + de/por. claro=True para fundo escuro."""
    corpo = BRANCO if claro else AZUL
    nome = m.sprite_texto(nome_curto(o["nome"], 48, larg - 20), 48, larg - 20, peso="Bold", cor=corpo, entrelinha=1.1)
    fde, fpor, ff = m.fonte(46, "SemiBold"), m.fonte(108, "Black"), m.fonte(38, "SemiBold")
    de = "de " + moeda(o["preco_antigo"])
    por = moeda(o["preco"])
    forma = o.get("forma_preco") or ""
    alt = nome.height + 70 + 130 + 10
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    img.alpha_composite(nome, (0, 0))
    g = ImageDraw.Draw(img)
    y = nome.height + 6
    g.text((10, y), de, font=fde, fill=LILAS if claro else CINZA)
    wde = fde.getlength(de)
    g.line([(10 + fde.getlength("de "), y + 32), (10 + wde, y + 32)], fill=VERMELHO, width=6)
    y += 58
    g.text((6, y), por, font=fpor, fill=LIMAO if claro else VIOLETA)
    if forma:
        g.text((14 + fpor.getlength(por) + 18, y + 58), forma, font=ff, fill=LILAS if claro else CINZA)
    return img


def pilula_loja(o):
    return m.sprite_pilula(o["plataforma"], 34, fundo=VIOLETA, cor=BRANCO, peso="Bold", pad=(26, 10))


# ---------------- Instagram (1080x1350) ----------------
def slide_produto(n, total, o):
    img = p.fundo(n, total)
    x0, y0, x1, y1 = 70, 200, p.PW - 70, 1170
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((x0, y0, x1, y1), radius=44, fill=BRANCO)
    fq = foto_quadro(o, x1 - x0 - 60, 560)
    img.alpha_composite(fq, (x0 + 30, y0 + 30))
    loja = pilula_loja(o)
    img.alpha_composite(loja, (x0 + 40, y0 + 40))
    s = selo_desconto(o["desconto"])
    img.alpha_composite(s, (x1 - s.width + 20, y0 - 30))
    b = bloco_preco(o, x1 - x0 - 80)
    img.alpha_composite(b, (x0 + 40, y0 + 620))
    r = m.sprite_texto(f"Preço conferido em {HOJE}  •  pode mudar", 32, 920, peso="Medium", cor=LILAS, alinhar="center")
    img.alpha_composite(r, (70, 1190))
    a = m.sprite_pilula("link na bio  >  opapaiachou.com.br", 34, fundo=LIMAO, cor=AZUL, peso="Bold")
    img.alpha_composite(a, ((p.PW - a.width) // 2, 1250))
    return img


def carrossel(pasta, kicker, titulo, sub, ofertas, fecho):
    T = len(ofertas) + 2
    slides = [p.capa(1, T, kicker, titulo, sub)]
    slides += [slide_produto(i + 2, T, o) for i, o in enumerate(ofertas)]
    slides.append(p.cta(T, T, fecho, "VER TODOS NO SITE", "opapaiachou.com.br",
                        rodape="Toque no link da bio  •  links de afiliado"))
    p.salvar(slides, pasta)
    legenda = "\n".join(f"{i + 1}. {o['nome'][:60]} ({o['plataforma']}): {moeda(o['preco'])}"
                        for i, o in enumerate(ofertas))
    with open(os.path.join(pasta, "produtos.txt"), "w", encoding="utf-8") as f:
        f.write(legenda + "\n")


# ---------------- TikTok (1080x1920) ----------------
def video(arquivo, kicker, gancho, fala_gancho, ofertas, fecho, fala_fecho):
    import lote3 as L
    r = L.Roteiro()
    maior = max(int(round(o["desconto"])) for o in ofertas)

    def hook(c, ts, ini, fim):
        y = gancho_kicker(c, kicker, ini, 330)
        c.add(Pop(numero_grande(f"{maior}%", tam=300), 70, y, ini + 0.2, 0.45, 0.2, pulsa=0.02, sfx="ding"))
        els, h = palavras(gancho, 96, 920, 80, y + 380, ini + 0.6)
        c.add(els)
    r.cena([fala_gancho], None, L.CANTO, hook, cauda=0.4, minimo=2.4)

    for i, o in enumerate(ofertas):
        def cena_prod(c, ts, ini, fim, o=o, i=i):
            k = m.sprite_pilula(f"ACHADO {i + 1}  •  {o['plataforma'].upper()}", 38)
            c.add(Pop(k, 80, 270, ini + 0.05, 0.3, 0.4, sfx=None))
            fq = foto_quadro(o, 920, 620, raio=40)
            c.add(Desliza(fq, 80, 360, ini + 0.05, 260, 0))
            c.add(Pop(selo_desconto(o["desconto"], 230), 790, 300, ts[0] + 0.5, 0.35, 0.3, pulsa=0.03, sfx="buzz"))
            b = bloco_preco(o, 920, claro=True)
            c.add(Desliza(b, 80, 1010, ts[0] + 0.25, 0, 90, sfx="pop"))
        fala = (f"{nome_falado(o['nome'])}, de {reais(o['preco_antigo'])} por {reais(o['preco'])}.")
        r.cena([fala], "swipe", L.CANTO, cena_prod, cauda=0.45, minimo=2.6)

    def offer(c, ts, ini, fim):
        y = 520 + 230 + 40
        els, h = palavras(fecho, 92, 920, 80, y, ts[0] + 0.1, alinhar="center")
        c.add(els)
        b = m.sprite_botao("VER NO SITE", "opapaiachou.com.br • link na bio")
        yb = y + h + 50
        tt = ts[-1] + 0.6
        c.add(Apertar(b, (W - b.width) // 2, yb, ts[0] + 0.6, tt))
        c.add(Toque(W // 2 + 330, yb + 125, tt))
        rr = m.sprite_texto(f"Preços de {HOJE}, podem mudar  •  links de afiliado", 36, 920, peso="SemiBold",
                            cor=LILAS, alinhar="center")
        c.add(Desliza(rr, 70, yb + b.height + 40, ts[-1], 0, 60, sfx="pop"))
    r.cena(fala_fecho, "zoom", L.TOPO, offer, cauda=0.8)
    L.render(r, arquivo)
    print("ok", arquivo, round(r.cenas[-1].fim, 1), "s")


# ---------------- lote da semana ----------------
SEM_GAMER = {"Casa e cozinha", "Moda", "Fitness", "Crianças", "Tecnologia útil", "Maquiagem e beleza", "Presentes", "Escola"}

def dia_23():
    pasta = os.path.join(SAIDA, "post_semana-23-11")
    carrossel(pasta, "BLACK FRIDAY ANTECIPADA", "Caiu de preço *hoje*", "5 achados conferidos pelo Papai",
              escolher(5, categorias=SEM_GAMER), "Tem *300 achados* no site do Papai")
    video(os.path.join(SAIDA_V, "tiktok-" + os.path.basename(pasta)[12:] + ".mp4"), "BLACK FRIDAY ANTECIPADA", "de desconto em achados *de hoje*",
          "Olha o que o Papai achou hoje!", escolher(3, categorias=SEM_GAMER),
          "Mais de *300 achados* no site", ["Tem mais de trezentos achados no site do Papai.", "Link na bio!"])


def dia_24():
    pasta = os.path.join(SAIDA, "post_semana-24-11")
    carrossel(pasta, "SETUP GAMER", "Gamer *em promoção*", "Headset, teclado, mouse e mais",
              escolher(5, categorias={"Gamer"}, min_desc=10), "Filtro *Gamer* no site do Papai")
    video(os.path.join(SAIDA_V, "tiktok-" + os.path.basename(pasta)[12:] + ".mp4"), "SETUP GAMER", "de desconto no *setup gamer*",
          "Setup gamer mais barato? O Papai achou!", escolher(3, categorias={"Gamer"}, min_desc=10),
          "Tem filtro *Gamer* no site", ["No site do Papai tem até filtro gamer.", "Link na bio!"])


def dia_25():
    pasta = os.path.join(SAIDA, "post_semana-25-11")
    carrossel(pasta, "CASA E COZINHA", "Casa *abaixo de R$ 150*", "Achados pra casa com desconto de verdade",
              escolher(5, categorias={"Casa e cozinha"}, preco_max=150), "Mais achados de *casa* no site")
    video(os.path.join(SAIDA_V, "tiktok-" + os.path.basename(pasta)[12:] + ".mp4"), "CASA E COZINHA", "de desconto pra *sua casa*",
          "Achados pra casa com desconto de verdade!", escolher(3, categorias={"Casa e cozinha"}),
          "Casa, cozinha e muito mais *no site*", ["Tem muito mais pra casa no site do Papai.", "Link na bio!"])


def dia_26():
    pasta = os.path.join(SAIDA, "post_semana-26-11")
    carrossel(pasta, "AMANHÃ É BLACK FRIDAY", "Esporte e moda *em queda*", "Tênis, roupas e fitness",
              escolher(5, categorias={"Fitness", "Moda"}), "Amanhã tem *mais achados* no site")
    video(os.path.join(SAIDA_V, "tiktok-" + os.path.basename(pasta)[12:] + ".mp4"), "AMANHÃ É BLACK FRIDAY", "de desconto *um dia antes*",
          "Um dia antes da blék fráidei e já tem isso!", escolher(3, categorias={"Fitness", "Moda", "Crianças"}),
          "Amanhã o site *atualiza o dia todo*", ["Amanhã o site do Papai atualiza o dia todo.", "Link na bio!"])


def atracao():
    import atracao as a
    a.gerar()


LOTE = {"23-11": dia_23, "24-11": dia_24, "25-11": dia_25, "26-11": dia_26, "atracao": atracao}
PADRAO = ["atracao"]  # o que o workflow renderiza a cada push (os dias 23 a 26 já foram publicados)


def main(dias=None):
    os.chdir(AQUI)
    os.makedirs(SAIDA_V, exist_ok=True)
    for d in dias or PADRAO:
        LOTE[d]()
    print("ok semana")


if __name__ == "__main__":
    main(sys.argv[1:])
