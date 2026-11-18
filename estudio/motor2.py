"""Motor v2: transições, texto palavra por palavra, carimbos, toques, scanner e efeitos sonoros."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import motor as m
from motor import W, H, FPS, AZUL, VIOLETA, LIMAO, LILAS, BRANCO, AZUL_CARD, fonte, clamp, ease_out, back_out

VERMELHO = (255, 77, 109)


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def com_alpha(img, a):
    if a >= 0.999:
        return img
    img = img.copy()
    img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    return img


def escala(img, s):
    if abs(s - 1) < 1e-3:
        return img, 0, 0
    nw, nh = max(1, int(img.width * s)), max(1, int(img.height * s))
    return img.resize((nw, nh), Image.BILINEAR), (img.width - nw) // 2, (img.height - nh) // 2


# ---------------- sprites extras ----------------
def icone(tipo, d=110):
    img = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    w = max(6, d // 10)
    if tipo == "ok":
        g.ellipse((0, 0, d - 1, d - 1), fill=LIMAO)
        g.line([(d * .26, d * .52), (d * .44, d * .70), (d * .76, d * .32)], fill=AZUL, width=w, joint="curve")
    elif tipo == "x":
        g.ellipse((0, 0, d - 1, d - 1), fill=VERMELHO)
        g.line([(d * .32, d * .32), (d * .68, d * .68)], fill=BRANCO, width=w)
        g.line([(d * .68, d * .32), (d * .32, d * .68)], fill=BRANCO, width=w)
    elif tipo == "alerta":
        g.polygon([(d / 2, 4), (d - 4, d - 8), (4, d - 8)], fill=(255, 196, 0))
        f = fonte(int(d * .62), "Black")
        g.text((d / 2 - f.getlength("!") / 2, d * .2), "!", font=f, fill=AZUL)
    return img


def carimbo(texto, cor, tam=88):
    f = fonte(tam, "Black")
    tw = f.getlength(texto)
    asc, desc = f.getmetrics()
    w, h = int(tw + 80), int(asc + desc + 50)
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=24, outline=cor, width=12)
    g.text((60, 40), texto, font=f, fill=cor)
    return img.rotate(-12, resample=Image.BICUBIC, expand=True)


def cartao_preco(de, por):
    w, h = 820, 420
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, w - 1, h - 1), radius=44, fill=BRANCO)
    g.text((60, 50), "DE", font=fonte(44, "Bold"), fill=(120, 110, 160))
    g.text((60, 100), de, font=fonte(92, "Bold"), fill=(120, 110, 160))
    g.text((60, 230), "POR", font=fonte(44, "Bold"), fill=AZUL)
    g.text((60, 270), por, font=fonte(118, "Black"), fill=VIOLETA)
    return img


def cartao_produto(nome, nota, vendas, extra, largura=900):
    h = 300
    img = Image.new("RGBA", (largura, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, largura - 1, h - 1), radius=40, fill=BRANCO)
    # "foto" ilustrativa
    g.rounded_rectangle((30, 30, 270, 270), radius=30, fill=(232, 226, 255))
    g.ellipse((105, 95, 195, 185), outline=VIOLETA, width=12)
    g.line([(180, 175), (225, 220)], fill=VIOLETA, width=16)
    g.text((300, 40), nome, font=fonte(58, "Black"), fill=AZUL)
    g.text((300, 122), f"{nota}   •   {vendas}", font=fonte(44, "SemiBold"), fill=(80, 70, 130))
    g.text((300, 192), extra, font=fonte(44, "Bold"), fill=VIOLETA)
    return img


def botao_enquete(texto, cor=BRANCO, fundo=VIOLETA, largura=420):
    f = fonte(72, "Black")
    h = 150
    img = Image.new("RGBA", (largura, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, largura - 1, h - 1), radius=40, fill=fundo, outline=LIMAO, width=6)
    asc, desc = f.getmetrics()
    g.text(((largura - f.getlength(texto)) / 2, (h - asc - desc) / 2 - 4), texto, font=f, fill=cor)
    return img


def numero_grande(texto, tam=520, cor=LIMAO):
    f = fonte(tam, "Black")
    asc, desc = f.getmetrics()
    w = int(f.getlength(texto)) + 40
    img = Image.new("RGBA", (w, asc + desc + 20), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((20, 0), texto, font=f, fill=cor)
    return img


# ---------------- elementos animados ----------------
class El:
    t0 = 0.0
    sfx = None

    def draw(self, cam, t):
        pass


class Pop(El):
    """Entra com escala (salto) e, opcional, flutua/pulsa."""
    def __init__(self, img, x, y, t0, dur=0.4, de=0.3, flutua=0, pulsa=0, sfx="pop", rot=0):
        self.img, self.x, self.y, self.t0, self.dur, self.de = img, x, y, t0, dur, de
        self.flutua, self.pulsa, self.sfx, self.rot = flutua, pulsa, sfx, rot

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0:
            return
        s = self.de + (1 - self.de) * back_out(p) if p < 1 else 1.0
        if self.pulsa and p >= 1:
            s *= 1 + self.pulsa * math.sin((t - self.t0) * 2 * math.pi * 2)  # 2 Hz = 120 bpm
        dy = self.flutua * math.sin((t - self.t0) * 2 * math.pi * 0.7) if self.flutua else 0
        img = self.img
        if self.rot and p < 1:
            img = img.rotate(self.rot * (1 - ease_out(p)), resample=Image.BILINEAR, expand=True)
        img, ox, oy = escala(img, s)
        img = com_alpha(img, clamp(p * 3))
        cam.alpha_composite(img, (int(self.x + ox), int(self.y + oy + dy)))


class Desliza(El):
    def __init__(self, img, x, y, t0, dx=300, dy=0, dur=0.4, sfx="whoosh"):
        self.img, self.x, self.y, self.t0, self.dx, self.dy, self.dur, self.sfx = img, x, y, t0, dx, dy, dur, sfx

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0:
            return
        a = ease_out(p)
        cam.alpha_composite(com_alpha(self.img, clamp(p * 2.5)),
                            (int(self.x + (1 - a) * self.dx), int(self.y + (1 - a) * self.dy)))


class Carimbo(El):
    def __init__(self, img, x, y, t0, sfx="buzz"):
        self.img, self.x, self.y, self.t0, self.sfx = img, x, y, t0, sfx

    def draw(self, cam, t):
        p = (t - self.t0) / 0.22
        if p <= 0:
            return
        s = 2.4 - 1.4 * ease_out(p) if p < 1 else 1.0
        img, ox, oy = escala(self.img, s)
        cam.alpha_composite(com_alpha(img, clamp(p * 2)), (int(self.x + ox), int(self.y + oy)))


class Risco(El):
    def __init__(self, x1, y, x2, t0, dur=0.3, cor=VERMELHO, larg=14, sfx="swish"):
        self.x1, self.y, self.x2, self.t0, self.dur, self.cor, self.larg, self.sfx = x1, y, x2, t0, dur, cor, larg, sfx

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0:
            return
        xe = self.x1 + (self.x2 - self.x1) * ease_out(p)
        ImageDraw.Draw(cam).line([(self.x1, self.y), (xe, self.y)], fill=self.cor, width=self.larg)


class Toque(El):
    """Dedo/cursor que toca num ponto e gera ondas."""
    def __init__(self, x, y, t0, sfx="tap"):
        self.x, self.y, self.t0, self.sfx = x, y, t0, sfx

    def draw(self, cam, t):
        lt = t - self.t0
        if lt < -0.35 or lt > 0.9:
            return
        g = ImageDraw.Draw(cam)
        if lt < 0:  # aproximação
            a = ease_out((lt + 0.35) / 0.35)
            cx, cy = self.x + (1 - a) * 160, self.y + (1 - a) * 220
            r = 46
        else:
            cx, cy, r = self.x, self.y, 46 - 10 * clamp(lt / 0.1) + 10 * clamp((lt - 0.1) / 0.15)
            for k in range(2):
                q = clamp((lt - k * 0.12) / 0.6)
                if 0 < q < 1:
                    rr = 50 + 160 * q
                    g.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=BRANCO + (int(220 * (1 - q)),), width=8)
        g.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 200), outline=AZUL + (255,), width=6)


class Apertar(El):
    """Botão que já está na tela e encolhe no momento do toque."""
    def __init__(self, img, x, y, t0, t_toque, dur=0.45, pulsa=0.03, depois=None):
        self.img, self.x, self.y, self.t0, self.tt, self.dur, self.pulsa = img, x, y, t0, t_toque, dur, pulsa
        self.depois = depois
        self.sfx = "pop"

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0:
            return
        s = 0.3 + 0.7 * back_out(p) if p < 1 else 1 + self.pulsa * math.sin((t - self.t0) * 4 * math.pi)
        d = t - self.tt
        if 0 <= d < 0.25:
            s *= 1 - 0.08 * math.sin(d / 0.25 * math.pi)
        base = self.depois if (self.depois is not None and d >= 0.08) else self.img
        img, ox, oy = escala(base, s)
        cam.alpha_composite(com_alpha(img, clamp(p * 3)), (int(self.x + ox), int(self.y + oy)))


class Scanner(El):
    def __init__(self, x, y, w, h, t0, dur=0.7, sfx="scan"):
        self.x, self.y, self.w, self.h, self.t0, self.dur, self.sfx = x, y, w, h, t0, dur, sfx

    def draw(self, cam, t):
        p = (t - self.t0) / self.dur
        if p <= 0 or p >= 1:
            return
        yy = self.y + self.h * ease_io(p)
        g = ImageDraw.Draw(cam)
        for k in range(30):
            a = int(120 * (1 - k / 30))
            g.line([(self.x, yy - k), (self.x + self.w, yy - k)], fill=LIMAO + (a,), width=1)
        g.line([(self.x - 10, yy), (self.x + self.w + 10, yy)], fill=LIMAO + (255,), width=8)


class Contador(El):
    """Números trocando com 'flip' (ex.: 10, 9, 8, 7)."""
    def __init__(self, valores, cx, cy, t0, passo=0.5, sfx="tick"):
        self.sprites = [numero_grande(str(v)) for v in valores]
        self.cx, self.cy, self.t0, self.passo, self.sfx = cx, cy, t0, passo, sfx
        self.n = len(valores)

    def tempos(self):
        return [self.t0 + i * self.passo for i in range(self.n)]

    def draw(self, cam, t):
        lt = t - self.t0
        if lt < 0:
            return
        i = min(self.n - 1, int(lt / self.passo))
        sp = self.sprites[i]
        q = (lt - i * self.passo) / 0.18
        sy = 0.4 + 0.6 * back_out(q) if q < 1 else 1.0
        img = sp.resize((sp.width, max(1, int(sp.height * sy))), Image.BILINEAR)
        cam.alpha_composite(img, (int(self.cx - sp.width / 2), int(self.cy - img.height / 2)))


def palavras(texto, tam, largura, x, y, t0, passo=0.09, peso="Black", alinhar="left", entrelinha=1.06, sfx_cada=False):
    """Divide o texto em palavras que entram uma a uma. Retorna (elementos, altura)."""
    f = fonte(tam, peso)
    linhas = m.quebrar(texto, f, largura)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * entrelinha)
    esp = f.getlength(" ")
    els, k = [], 0
    for i, linha in enumerate(linhas):
        total = sum(f.getlength(w) for w, _ in linha) + esp * (len(linha) - 1)
        xx = x if alinhar == "left" else x + (largura - total) / 2
        for w, dest in linha:
            sp = Image.new("RGBA", (int(f.getlength(w)) + 20, lh + 20), (0, 0, 0, 0))
            ImageDraw.Draw(sp).text((10, 10), w, font=f, fill=LIMAO if dest else BRANCO)
            els.append(Pop(sp, xx - 10, y + i * lh - 10, t0 + k * passo, 0.32, 0.2,
                           sfx=("pop" if (sfx_cada or k == 0) else None)))
            xx += f.getlength(w) + esp
            k += 1
    return els, lh * len(linhas)


# ---------------- cenas e transições ----------------
class Cena:
    def __init__(self, inicio, fim, transicao="swipe"):
        self.inicio, self.fim, self.transicao, self.els = inicio, fim, transicao, []

    def add(self, *els):
        for e in els:
            if isinstance(e, list):
                self.els.extend(e)
            else:
                self.els.append(e)

    def camada(self, t):
        cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for e in self.els:
            e.draw(cam, t)
        return cam


TR = 0.32  # duração da transição


def particulas(fr, t):
    rnd = random.Random(3)
    g = ImageDraw.Draw(fr)
    f = fonte(44, "Black")
    for i in range(16):
        x0, v, fase = rnd.uniform(60, W - 60), rnd.uniform(40, 90), rnd.uniform(0, H)
        y = (fase - t * v) % (H + 100) - 50
        if i % 4 == 0:
            g.text((x0, y), "%", font=f, fill=LIMAO + (60,))
        else:
            r = 5 if i % 2 else 3
            g.ellipse((x0 - r, y - r, x0 + r, y + r), fill=LILAS + (90,))


def compor(cenas, t, base):
    fr = base.copy()
    particulas(fr, t)
    for i, c in enumerate(cenas):
        if t < c.inicio - TR / 2 or t >= c.fim + TR / 2:
            continue
        cam = c.camada(clamp(t, c.inicio, c.fim + 1))
        # transição de entrada (definida pela cena) e de saída (definida pela próxima)
        prox = cenas[i + 1] if i + 1 < len(cenas) else None
        if t < c.inicio + TR / 2 and i > 0:
            p = ease_io((t - (c.inicio - TR / 2)) / TR)
            cam = entrar(cam, c.transicao, p)
            if p <= 0:
                continue
        if prox and t > c.fim - TR / 2:
            p = ease_io((t - (c.fim - TR / 2)) / TR)
            cam = sair(cam, prox.transicao, p)
            if cam is None:
                continue
        fr.alpha_composite(cam)
    # faixa / flash da transição
    for c in cenas[1:]:
        d = t - c.inicio
        if -TR / 2 <= d <= TR / 2:
            p = (d + TR / 2) / TR
            if c.transicao == "swipe":
                faixa(fr, p)
            elif c.transicao == "flash":
                a = int(200 * (1 - abs(p - 0.5) * 2))
                fr.alpha_composite(Image.new("RGBA", (W, H), LIMAO + (a,)))
    g = ImageDraw.Draw(fr)
    g.rectangle((0, 0, int(W * t / cenas[-1].fim), 10), fill=LIMAO)
    return fr


def entrar(cam, tipo, p):
    if tipo == "swipe":
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(cam, (int(W * (1 - p)), 0))
        return out
    if tipo == "zoom":
        img, ox, oy = escala(cam, 0.8 + 0.2 * p)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(com_alpha(img, p), (ox, oy))
        return out
    return com_alpha(cam, p)


def sair(cam, tipo, p):
    if p >= 1:
        return None
    if tipo == "swipe":
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(cam, (-int(W * p), 0))
        return out
    if tipo == "zoom":
        sc = 1 + 0.35 * p
        nw, nh = int(W * sc), int(H * sc)
        img = cam.resize((nw, nh), Image.BILINEAR)
        ox, oy = (nw - W) // 2, (nh - H) // 2
        return com_alpha(img.crop((ox, oy, ox + W, oy + H)), 1 - p)
    return com_alpha(cam, 1 - p)


def faixa(fr, p):
    """Faixa diagonal limão que cruza a tela no swipe."""
    g = ImageDraw.Draw(fr)
    x = -900 + (W + 1800) * p
    g.polygon([(x, 0), (x + 260, 0), (x + 260 - 700, H), (x - 700, H)], fill=LIMAO + (235,))
    g.polygon([(x + 300, 0), (x + 340, 0), (x + 340 - 700, H), (x + 300 - 700, H)], fill=VIOLETA + (235,))


# ---------------- áudio ----------------
SR = 44100


def _env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-t / d)


def sfx(tipo, rng):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    if tipo == "pop":
        f = 520 + 600 * np.exp(-t * 30)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.05) * 0.5
    if tipo == "whoosh":
        x = rng.normal(0, 1, n)
        k = np.linspace(0.02, 0.4, n)
        y = np.zeros(n); acc = 0
        for i in range(n):
            acc += k[i] * (x[i] - acc); y[i] = acc
        e = np.sin(np.pi * np.clip(t / 0.35, 0, 1)) * (t < 0.35)
        return y * e * 0.9
    if tipo == "swish":
        x = rng.normal(0, 1, n) * _env(n, 0.01, 0.08)
        return np.convolve(x, np.ones(4) / 4, "same") * 0.35
    if tipo == "buzz":
        sq = np.sign(np.sin(2 * np.pi * 110 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 116 * t))
        return sq * (t < 0.3) * _env(n, 0.005, 0.25) * 0.22
    if tipo == "ding":
        return (np.sin(2 * np.pi * 1318 * t) + 0.6 * np.sin(2 * np.pi * 1975 * t)) * _env(n, 0.002, 0.18) * 0.35
    if tipo == "tick":
        return np.sin(2 * np.pi * 1800 * t) * _env(n, 0.001, 0.015) * 0.6
    if tipo == "tap":
        return np.sin(2 * np.pi * 900 * t) * _env(n, 0.001, 0.03) * 0.45
    if tipo == "scan":
        f = 300 + 900 * t / 0.5
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.02, 0.4) * 0.12
    return np.zeros(n)


def eventos_som(cenas):
    ev = []
    for i, c in enumerate(cenas):
        if i > 0 and c.transicao in ("swipe", "zoom", "flash"):
            ev.append((c.inicio - 0.15, "whoosh"))
        for e in c.els:
            if isinstance(e, Contador):
                ev += [(tt, "tick") for tt in e.tempos()]
            elif getattr(e, "sfx", None):
                ev.append((e.t0, e.sfx))
            if isinstance(e, Apertar):
                ev.append((e.tt, "tap"))
    return ev


def gancho_kicker(c, texto, t0, y=380):
    k = m.sprite_pilula(texto, 40)
    c.add(Pop(k, 80, y, t0, 0.35, 0.4))
    return y + k.height + 30
