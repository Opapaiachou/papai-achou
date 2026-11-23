"""Vídeo de atração: apresenta o site do Papai Achou (tudo o que tem, lojas, categorias,
atualização automática) com os números reais de docs/ofertas.json.
Saída: saida3/atracao.mp4 (9:16, para TikTok e Reels)."""
import json, os
from PIL import Image, ImageDraw
import motor as m
from motor2 import (El, Pop, Desliza, Carimbo, Toque, Apertar, palavras, gancho_kicker, carimbo, numero_grande,
                    ease_out, ease_io, clamp, W, H, LIMAO, VIOLETA, LILAS, AZUL, BRANCO)
import semana as s

LOJAS = ["Nike", "adidas", "Kabum", "Magalu", "Mercado Livre"]
CATS = [("Casa e cozinha", "Casa"), ("Fitness", "Fitness"), ("Escola", "Escola"), ("Moda", "Moda"),
        ("Maquiagem e beleza", "Beleza"), ("Tecnologia útil", "Tecnologia"), ("Gamer", "Gamer"),
        ("Crianças", "Crianças"), ("Presentes", "Presentes")]
HORAS = ["7h", "10h", "13h", "16h", "19h", "22h"]
# marcas conhecidas: só aparecem no vídeo as que estão de fato em produtos do site
MARCAS = ["Samsung", "JBL", "Tramontina", "Mondial", "Olympikus", "Mizuno", "Philco", "Motorola", "Lenovo",
          "Logitech", "Redragon", "Puma", "Under Armour", "Fila", "Oster", "Philips", "LG", "Multilaser", "Casio"]
# para a foto de cada categoria ser um produto típico dela
DICA = {"Escola": r"escol|estojo|lancheira|caderno", "Fitness": r"t[eê]nis|legging|garrafa|whey|creatina|academia",
        "Casa e cozinha": r"panela|pote|air fryer|fritadeira|jogo de cama|garrafa", "Gamer": r"headset|teclado|mouse"}


def marcas_no_site(ofs):
    import re
    achadas = []
    for mk in MARCAS:
        if any(re.search(r"\b" + re.escape(mk) + r"\b", o["nome"], re.I) for o in ofs):
            achadas.append(mk)
    return achadas[:10]


class ContaAte(El):
    """Número que sobe de 0 até o valor (com +), e depois pulsa."""
    def __init__(self, valor, x, y, t0, dur=1.1, tam=330, sfx="ding"):
        self.valor, self.x, self.y, self.t0, self.dur, self.tam, self.sfx = valor, x, y, t0, dur, tam, sfx
        self.cache = {}

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0:
            return
        v = int(round(self.valor * ease_out(min(1, p)) / 10) * 10) if p < 1 else self.valor
        if v not in self.cache:
            self.cache[v] = numero_grande(f"+{v}", tam=self.tam)
        img = self.cache[v]
        if p >= 1:
            sc = 1 + 0.025 * abs(__import__("math").sin((t - self.t0) * 4))
            img = img.resize((int(img.width * sc), int(img.height * sc)))
        cam.alpha_composite(img, (self.x, self.y))


def ofertas():
    return json.load(open(s.OFERTAS, encoding="utf-8"))


def melhor_da_categoria(ofs, cat):
    import re
    cands = [o for o in ofs if o.get("categoria") == cat and o.get("foto")]
    if cat in DICA:
        tipicos = [o for o in cands if re.search(DICA[cat], o["nome"], re.I)]
        cands = tipicos or cands
    cands.sort(key=lambda o: -(o.get("desconto") or 0))
    for o in cands[:8]:
        if s.foto(o["foto"]) is not None:
            return o
    return None


def celula(o, rotulo, larg=290, alt=300):
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, larg - 1, alt - 1), radius=30, fill=BRANCO)
    if o is not None:
        f = s.foto(o["foto"]).copy()
        f.thumbnail((larg - 40, alt - 100), Image.LANCZOS)
        img.alpha_composite(f, ((larg - f.width) // 2, 18 + (alt - 100 - f.height) // 2))
    g.rounded_rectangle((0, alt - 72, larg - 1, alt - 1), radius=30, fill=VIOLETA)
    g.rectangle((0, alt - 72, larg - 1, alt - 40), fill=VIOLETA)
    fn = m.fonte(40, "Black")
    g.text(((larg - fn.getlength(rotulo)) / 2, alt - 64), rotulo, font=fn, fill=BRANCO)
    return img


def mini_card(o, larg=230, alt=300):
    img = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, larg - 1, alt - 1), radius=18, fill=BRANCO)
    f = s.foto(o["foto"])
    if f is not None:
        f = f.copy()
        f.thumbnail((larg - 24, 160), Image.LANCZOS)
        img.alpha_composite(f, ((larg - f.width) // 2, 12 + (160 - f.height) // 2))
    if (o.get("desconto") or 0) >= 5:
        sel = m.sprite_pilula(f"-{int(round(o['desconto']))}%", 22, pad=(12, 4))
        img.alpha_composite(sel, (larg - sel.width - 8, 8))
    nome = m.sprite_texto(s.nome_curto(o["nome"], 20, larg - 30), 20, larg - 30, peso="SemiBold", cor=AZUL)
    img.alpha_composite(nome, (6, 176))
    g.text((14, 232), s.moeda(o["preco"]), font=m.fonte(30, "Black"), fill=VIOLETA)
    bt = m.sprite_pilula("Comprar", 18, fundo=VIOLETA, cor=BRANCO, peso="Bold", pad=(14, 4))
    img.alpha_composite(bt, (larg - bt.width - 10, alt - bt.height - 10))
    return img


def tela_site(ofs, larg=520):
    """Imagem alta com a 'vitrine' do site (2 colunas de cards) para rolar dentro do celular."""
    escolhidos = s.escolher(14, min_desc=15)
    cards = [mini_card(o) for o in escolhidos]
    gap = 20
    alt = 60 + ((len(cards) + 1) // 2) * (300 + gap)
    img = Image.new("RGBA", (larg, alt), (245, 242, 255, 255))
    for i, c in enumerate(cards):
        x = gap + (i % 2) * (230 + gap)
        y = 40 + (i // 2) * (300 + gap)
        img.alpha_composite(c, (x, y))
    return img


class Celular(El):
    """Celular com o site rolando dentro (a vitrine sobe devagar)."""
    def __init__(self, tela, x, y, t0, dur_rolagem, sfx="whoosh"):
        self.tela, self.x, self.y, self.t0, self.dur, self.sfx = tela, x, y, t0, dur_rolagem, sfx
        self.w, self.h = 580, 1060
        moldura = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        g = ImageDraw.Draw(moldura)
        g.rounded_rectangle((0, 0, self.w - 1, self.h - 1), radius=70, fill=(14, 6, 50), outline=LIMAO, width=6)
        self.moldura = moldura
        topo = Image.new("RGBA", (520, 150), (91, 46, 255, 255))
        gt = ImageDraw.Draw(topo)
        gt.text((24, 22), "papai achou", font=m.fonte(40, "Black"), fill=BRANCO)
        gt.text((24, 76), "opapaiachou.com.br", font=m.fonte(26, "SemiBold"), fill=LIMAO)
        x = 24
        for c in ["Todos", "Casa", "Fitness", "Gamer"]:
            p = m.sprite_pilula(c, 18, fundo=LIMAO if c == "Todos" else BRANCO, cor=AZUL, peso="Bold", pad=(12, 4))
            topo.alpha_composite(p, (x, 114))
            x += p.width + 8
        self.topo = topo

    def draw(self, cam, t):
        p = (t - self.t0) / 0.45
        if p <= 0:
            return
        dy = int((1 - ease_out(p)) * 500)
        a = clamp(p * 2)
        quadro = self.moldura.copy()
        visivel = self.h - 30 - 150 - 30
        rol = ease_io(clamp((t - self.t0 - 0.4) / self.dur)) * max(0, self.tela.height - visivel)
        janela = self.tela.crop((0, int(rol), 520, int(rol) + visivel))
        quadro.alpha_composite(self.topo, (30, 30))
        quadro.alpha_composite(janela, (30, 180))
        if a < 1:
            quadro.putalpha(quadro.getchannel("A").point(lambda v: int(v * a)))
        cam.alpha_composite(quadro, (self.x, self.y + dy))


def gerar():
    import lote3 as L
    ofs = ofertas()
    total = len(ofs)
    redondo = total // 10 * 10
    lojas = [l for l in LOJAS if any(o["plataforma"] == l for o in ofs)]
    r = L.Roteiro()
    BAIXO = (540, 1640, 300)

    # 1. Gancho: número de achados
    def hook(c, ts, ini, fim):
        y = gancho_kicker(c, "O SITE DO PAPAI ACHOU", ini, 330)
        c.add(ContaAte(redondo, 60, y, ini + 0.3))
        els, h = palavras("achados com *preço conferido*", 100, 920, 80, y + 410, ts[0] + 0.9)
        c.add(els)
    r.cena(["Cansou de caçar promoção?", f"O Papai já achou mais de {s.extenso(redondo)} pra você."],
           None, BAIXO, hook, cauda=0.4)

    # 2. Lojas: direto das marcas e grandes lojas
    marcas = marcas_no_site(ofs)

    def lojas_cena(c, ts, ini, fim):
        els, h = palavras("Direto das *marcas* e das *maiores lojas*", 88, 920, 80, 280, ts[0])
        c.add(els)
        y0 = 280 + h + 40
        passo = (ts[2] - ts[1]) / max(1, len(lojas))
        for i, nome in enumerate(lojas):
            pil = m.sprite_pilula(nome, 60, fundo=BRANCO if i % 2 else LIMAO, cor=AZUL, peso="Black", pad=(40, 20))
            x = 80 if i % 2 == 0 else 1000 - pil.width
            c.add(Pop(pil, x, y0 + (i // 2) * 150, ts[1] + i * passo, 0.35, 0.3, rot=(8 if i % 2 else -8)))
        # segunda onda: marcas que estão nos produtos do site, em pílulas menores (fluxo)
        x, y = 80, y0 + 3 * 150 + 20
        passo = (fim - ts[2] - 0.8) / max(1, len(marcas) + 1)
        for i, mk in enumerate(marcas + ["+ MUITO MAIS"]):
            ult = mk.startswith("+")
            pil = m.sprite_pilula(mk, 44 if not ult else 50, fundo=LIMAO if ult else VIOLETA,
                                  cor=AZUL if ult else BRANCO, peso="Black" if ult else "Bold", pad=(28, 14))
            if x + pil.width > 1000:
                x, y = 80, y + pil.height + 22
            c.add(Pop(pil, x, y, ts[2] + 0.3 + i * passo, 0.3, 0.3, sfx="pop" if ult or i % 2 == 0 else None))
            x += pil.width + 20
    falas_marcas = {"Samsung": "sâmsung", "JBL": "jota bê éle", "Olympikus": "olímpikus", "Philco": "fílco",
                    "Logitech": "lójitec", "Under Armour": "ânder ármor", "Puma": "puma", "LG": "éle gê"}
    ditas = ", ".join(falas_marcas.get(mk, mk.lower()) for mk in marcas[:5])
    falas_lojas = ["Tudo direto das marcas e das maiores lojas do Brasil:",
                   "Náiqui, adidas, Kabum, Magalu e Mercado Livre.",
                   f"Tem {ditas}, e muito mais marcas!"]
    r.cena(falas_lojas, "swipe", BAIXO, lojas_cena, cauda=0.8)

    # 3. Categorias com fotos reais
    def cats_cena(c, ts, ini, fim):
        els, h = palavras("Achado pra *toda a família*", 84, 920, 80, 280, ts[0])
        c.add(els)
        y0 = 280 + h + 30
        passo = (fim - ts[0] - 0.8) / len(CATS)
        for i, (cat, rot) in enumerate(CATS):
            cel = celula(melhor_da_categoria(ofs, cat), rot)
            x = 80 + (i % 3) * 315
            y = y0 + (i // 3) * 320
            c.add(Pop(cel, x, y, ts[0] + 0.4 + i * passo, 0.3, 0.3, sfx="pop"))
    r.cena(["Tem pra casa, treino, escola, moda, beleza,", "tecnologia, gamer, crianças e presentes."],
           "flash", (905, 1700, 230), cats_cena, cauda=0.5)

    # 4. Atualização automática
    def atualiza(c, ts, ini, fim):
        els, h = palavras("Atualiza *sozinho* 6x por dia", 100, 920, 80, 320, ts[0])
        c.add(els)
        y0 = 320 + h + 60
        for i, hr in enumerate(HORAS):
            p = m.sprite_pilula(hr, 70, fundo=VIOLETA, cor=BRANCO, peso="Black", pad=(40, 20))
            c.add(Pop(p, 80 + (i % 3) * 320, y0 + (i // 3) * 180, ts[0] + 0.5 + i * 0.25, 0.3, 0.3, sfx="tick"))
        c.add(Carimbo(carimbo("SEM DESCONTO FALSO", LIMAO, 64), 90, y0 + 420, ts[-1] + 0.3, sfx="buzz"))
    r.cena(["E o site atualiza sozinho, seis vezes por dia.", "Preço conferido, sem desconto falso."],
           "swipe", BAIXO, atualiza, cauda=0.6)

    # 5. Celular com o site rolando
    tela = tela_site(ofs)

    def site(c, ts, ini, fim):
        k = m.sprite_pilula("COMO FUNCIONA", 40)
        c.add(Pop(k, 80, 270, ini + 0.05, 0.3, 0.4, sfx=None))
        c.add(Celular(tela, 80, 360, ini + 0.1, fim - ini - 0.6))
        for i, (txt, t) in enumerate(zip(["Filtra", "Escolhe", "Compra"], ts)):
            p = m.sprite_pilula(f"{i + 1}. {txt}", 44, fundo=LIMAO, cor=AZUL, peso="Black", pad=(26, 14))
            c.add(Desliza(p, W - 50 - p.width, 600 + i * 150, t, 200, 0, sfx="pop"))
        c.add(Toque(250, 560, ts[0] + 0.5))
    r.cena(["Você filtra por categoria,", "escolhe o achado,", "e compra direto na loja."],
           "zoom", (905, 1640, 240), site, cauda=0.6, minimo=6.0)

    # 6. Chamada
    def cta(c, ts, ini, fim):
        y = 520 + 230 + 40
        els, h = palavras("Tudo isso no *site do Papai*", 92, 920, 80, y, ts[0] + 0.1, alinhar="center")
        c.add(els)
        b = m.sprite_botao("VER NO SITE", "opapaiachou.com.br • link na bio")
        yb = y + h + 50
        tt = ts[-1] + 0.6
        c.add(Apertar(b, (W - b.width) // 2, yb, ts[0] + 0.6, tt))
        c.add(Toque(W // 2 + 330, yb + 125, tt))
        rr = m.sprite_texto("Links de afiliado: você não paga nada a mais", 36, 920, peso="SemiBold",
                            cor=LILAS, alinhar="center")
        c.add(Desliza(rr, 70, yb + b.height + 40, ts[-1], 0, 60, sfx="pop"))
    r.cena(["Tá tudo no site do Papai.", "O link tá na bio!"], "zoom", L.TOPO, cta, cauda=0.9)

    os.makedirs(s.SAIDA_V, exist_ok=True)
    arq = os.path.join(s.SAIDA_V, "atracao.mp4")
    L.render(r, arq)
    print("ok", arq, round(r.cenas[-1].fim, 1), "s", total, "achados", lojas)
