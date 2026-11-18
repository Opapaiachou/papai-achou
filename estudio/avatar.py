"""Avatar falante do Papai: boca sincronizada com a voz, piscadas e movimento de cabeça."""
import math, os
import numpy as np
from PIL import Image, ImageDraw
from motor import LIMAO, LILAS, clamp
from motor2 import ease_io

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = Image.open(os.path.join(AQUI, "mascote.png")).convert("RGBA")
BARBA = (100, 55, 32, 255)
LABIO = (126, 70, 52, 255)
BOCA = (52, 16, 14, 255)
LINGUA = (176, 74, 74, 255)
PELE = (131, 78, 47, 255)
CILIO = (45, 22, 16, 255)


def envelope(voz, sr, fps, dur):
    """Abertura da boca (0..1) por quadro, a partir da energia da voz."""
    n = int(dur * fps)
    hop = sr / fps
    env = np.zeros(n)
    for i in range(n):
        a, b = int(i * hop), int((i + 1) * hop)
        seg = voz[a:b]
        env[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
    ref = np.percentile(env[env > 0], 90) if np.any(env > 0) else 1
    env = np.clip(env / (ref + 1e-9), 0, 1.2)
    env[env < 0.12] = 0
    # suaviza (ataque rápido, soltura lenta)
    out = np.zeros(n)
    for i in range(n):
        prev = out[i - 1] if i else 0
        out[i] = env[i] if env[i] > prev else prev * 0.55 + env[i] * 0.45
    return np.clip(out, 0, 1)


def olhar_camera(g):
    """Redesenha os olhos olhando para a frente (contato visual)."""
    for (x0, y0, x1, y1, cx, cy) in [(212, 257, 245, 273, 229.5, 265.5), (281, 245, 311, 261, 296.5, 253.5)]:
        g.ellipse((x0, y0, x1, y1), fill=(255, 255, 255, 255))
        r = 6.5
        g.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(58, 30, 22, 255))
        g.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(20, 10, 8, 255))
        g.ellipse((cx + 1, cy - 4, cx + 4, cy - 1), fill=(255, 255, 255, 255))
        g.arc((x0 - 1, y0 - 1, x1 + 1, y1 + 5), 190, 350, fill=CILIO, width=4)


def rosto(abertura, piscar, t):
    img = SRC.copy()
    g = ImageDraw.Draw(img)
    olhar_camera(g)
    if abertura > 0.06:
        cx, cy = 272, 331
        larg = 44 + 8 * math.sin(t * 9.0)          # varia entre "o" e "e"
        alt = 6 + 24 * abertura
        # cobre o sorriso original
        g.ellipse((cx - 33, cy - 13, cx + 33, cy + 15), fill=BARBA)
        # lábios
        g.ellipse((cx - larg / 2 - 4, cy - alt / 2 - 4, cx + larg / 2 + 4, cy + alt / 2 + 5), fill=LABIO)
        g.ellipse((cx - larg / 2, cy - alt / 2, cx + larg / 2, cy + alt / 2), fill=BOCA)
        # dentes de cima e língua
        g.chord((cx - larg / 2 + 3, cy - alt / 2, cx + larg / 2 - 3, cy - alt / 2 + max(6, alt * 0.55)), 180, 360, fill=(255, 255, 255, 255))
        if alt > 14:
            g.chord((cx - larg / 3, cy + alt / 2 - alt * 0.45, cx + larg / 3, cy + alt / 2 + 2), 180, 360, fill=LINGUA)
    if piscar > 0:
        for (x0, y0, x1, y1) in [(212, 255, 248, 276), (280, 243, 312, 264)]:
            h = (y1 - y0) * piscar
            g.rectangle((x0, y0, x1, y0 + h), fill=PELE)
            g.line((x0 + 2, y0 + h, x1 - 2, y0 + h), fill=CILIO, width=3)
    return img


def piscada(t):
    """Pisca a cada ~3,2 s (com variação), duração 0,16 s."""
    per = 3.2
    k = int(t / per)
    off = (k * 1.7) % 1.1
    lt = t - k * per - off
    if 0 <= lt < 0.16:
        return math.sin(lt / 0.16 * math.pi)
    return 0.0


def desenhar_avatar(frame, t, abertura, cx, cy, diam):
    img = rosto(abertura, piscada(t), t)
    d = int(diam)
    m = img.resize((d, d), Image.LANCZOS if d < 512 else Image.BICUBIC)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
    m.putalpha(mask)
    b = max(6, d // 36)
    tot = d + 4 * b
    av = Image.new("RGBA", (tot, tot), (0, 0, 0, 0))
    ga = ImageDraw.Draw(av)
    ga.ellipse((0, 0, tot - 1, tot - 1), fill=LIMAO)
    ga.ellipse((b, b, tot - 1 - b, tot - 1 - b), fill=LILAS)
    av.alpha_composite(m, (2 * b, 2 * b))
    ang = 1.6 * math.sin(t * 1.3) + 2.2 * abertura * math.sin(t * 5.0)
    av = av.rotate(ang, resample=Image.BICUBIC, expand=False)
    bob = -6 * abertura + 4 * math.sin(t * 2.1)
    frame.alpha_composite(av, (int(cx - tot / 2), int(cy - tot / 2 + bob)))


class Apresentador:
    """Guarda as posições do avatar por cena e interpola nas transições."""
    def __init__(self, env, fps):
        self.env, self.fps, self.keys = env, fps, []

    def chave(self, t, cx, cy, diam):
        self.keys.append((t, cx, cy, diam))

    def pos(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1:]
        for (t0, *a), (t1, *b) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                p = ease_io((t - t0) / max(1e-6, t1 - t0))
                return tuple(x + (y - x) * p for x, y in zip(a, b))
        return ks[-1][1:]

    def desenhar(self, frame, t, entrada=0.0):
        i = min(len(self.env) - 1, int(t * self.fps))
        cx, cy, d = self.pos(t)
        if t < entrada + 0.5:  # pop de entrada
            from motor import back_out
            d *= 0.3 + 0.7 * back_out((t - entrada) / 0.5) if t >= entrada else 0
            if d <= 1:
                return
        desenhar_avatar(frame, t, float(self.env[i]), cx, cy, d)
