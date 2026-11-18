"""Motor de vídeos animados do Papai Achou (9:16, 1080x1920, 30 fps)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, "Outfit.ttf")

AZUL = (26, 11, 92)        # fundo do mascote / textos #1A0B5C
VIOLETA = (91, 46, 255)    # #5B2EFF
LIMAO = (198, 244, 50)     # #C6F432
LILAS = (185, 166, 255)
BRANCO = (255, 255, 255)
AZUL_CARD = (44, 22, 140)


def fonte(tam, peso="Bold"):
    f = ImageFont.truetype(FONTE, tam)
    f.set_variation_by_name(peso)
    return f


# ---------- utilidades de easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back_out(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------- texto com destaque *palavra* ----------
def quebrar(texto, f, largura):
    """Retorna linhas como listas de (palavra, destaque)."""
    palavras = []
    destaque = False
    for bruto in texto.split(" "):
        p = bruto
        ini = p.startswith("*")
        fim = p.endswith("*") and len(p) > 1
        if ini:
            destaque = True
            p = p[1:]
        if fim:
            p = p[:-1]
        palavras.append((p, destaque))
        if fim:
            destaque = False
    linhas, atual = [], []
    for p in palavras:
        teste = " ".join(w for w, _ in atual + [p])
        if atual and f.getlength(teste) > largura:
            linhas.append(atual)
            atual = [p]
        else:
            atual.append(p)
    if atual:
        linhas.append(atual)
    return linhas


def sprite_texto(texto, tam, largura, peso="Black", cor=BRANCO, cor_destaque=LIMAO, alinhar="left", entrelinha=1.08):
    f = fonte(tam, peso)
    linhas = quebrar(texto, f, largura)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * entrelinha)
    img = Image.new("RGBA", (largura + 20, lh * len(linhas) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    esp = f.getlength(" ")
    for i, linha in enumerate(linhas):
        total = sum(f.getlength(w) for w, _ in linha) + esp * (len(linha) - 1)
        x = 10 if alinhar == "left" else 10 + (largura - total) / 2
        y = 10 + i * lh
        for w, dest in linha:
            d.text((x, y), w, font=f, fill=cor_destaque if dest else cor)
            x += f.getlength(w) + esp
    return img


def sprite_pilula(texto, tam, fundo=LIMAO, cor=AZUL, pad=(34, 16), peso="ExtraBold"):
    f = fonte(tam, peso)
    tw = f.getlength(texto)
    asc, desc = f.getmetrics()
    w, h = int(tw + pad[0] * 2), int(asc + desc + pad[1] * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=fundo)
    d.text((pad[0], pad[1]), texto, font=f, fill=cor)
    return img


def sprite_item(num, texto, largura=920, tam=62):
    f = fonte(tam, "SemiBold")
    corpo = sprite_texto(texto, tam, largura - 200, peso="SemiBold", entrelinha=1.12)
    h = max(int(tam * 2.5), corpo.height + 50)
    img = Image.new("RGBA", (largura, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, largura - 1, h - 1), radius=36, fill=AZUL_CARD, outline=VIOLETA, width=4)
    # selo numerado
    cx, cy, r = 85, h // 2, 50
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LIMAO)
    fn = fonte(60, "Black")
    tw = fn.getlength(str(num))
    asc, desc = fn.getmetrics()
    d.text((cx - tw / 2, cy - (asc + desc) / 2 - 2), str(num), font=fn, fill=AZUL)
    img.alpha_composite(corpo, (160, (h - corpo.height) // 2))
    return img


def sprite_mascote(diam, anel=True):
    m = Image.open(os.path.join(AQUI, "mascote.png")).convert("RGBA").resize((diam, diam), Image.LANCZOS)
    mask = Image.new("L", (diam, diam), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diam - 1, diam - 1), fill=255)
    m.putalpha(mask)
    if not anel:
        return m
    borda = 14
    tot = diam + borda * 4
    img = Image.new("RGBA", (tot, tot), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, tot - 1, tot - 1), fill=LIMAO)
    d.ellipse((borda, borda, tot - 1 - borda, tot - 1 - borda), fill=LILAS)
    img.alpha_composite(m, (borda * 2, borda * 2))
    return img


def sprite_botao(texto, sub=None, largura=900):
    f = fonte(62, "Black")
    h = 150 if not sub else 190
    img = Image.new("RGBA", (largura, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 14, largura - 1, h + 13), radius=48, fill=(120, 150, 20))  # sombra
    d.rounded_rectangle((0, 0, largura - 1, h - 1), radius=48, fill=LIMAO)
    tw = f.getlength(texto)
    y = 38 if not sub else 30
    d.text(((largura - tw) / 2, y), texto, font=f, fill=AZUL)
    if sub:
        fs = fonte(38, "SemiBold")
        sw = fs.getlength(sub)
        d.text(((largura - sw) / 2, 112), sub, font=fs, fill=AZUL)
    return img


# ---------- fundo ----------
def fundo_base():
    img = Image.new("RGB", (W, H), AZUL)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-400, -300, 900, 900), fill=VIOLETA + (150,))
    g.ellipse((500, 1300, 1500, 2300), fill=VIOLETA + (110,))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    img = img.convert("RGBA")
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    for y in range(40, H, 60):
        for x in range(40, W, 60):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255, 28))
    # cabeçalho fixo
    icone = sprite_mascote(96, anel=False)
    img.alpha_composite(icone, (70, 120))
    d.text((190, 122), "Papai Achou", font=fonte(46, "Black"), fill=BRANCO)
    d.text((190, 176), "@opapaiachou", font=fonte(32, "Medium"), fill=LILAS)
    return img
