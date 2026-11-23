"""Lote 3: avatar falante + voz + estrutura Hook, Story, Offer."""
import sys, os, subprocess, wave
import numpy as np
import soundfile as sf
from PIL import Image
import motor as m
import motor2 as m2
from motor2 import (Cena, Pop, Desliza, Carimbo, Risco, Toque, Apertar, Scanner, Contador, palavras,
                    gancho_kicker, icone, carimbo, cartao_preco, cartao_produto, botao_enquete,
                    W, H, FPS, LIMAO, VIOLETA, LILAS, AZUL, BRANCO, VERMELHO)
from avatar import envelope, Apresentador

VOZ_DIR = os.environ.get("VOZ_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "voz"))
VOZ = os.environ.get("VOZ", "pm_alex")
SR_V = 24000
_kok = None


def tts(texto):
    global _kok
    if _kok is None:
        from kokoro_onnx import Kokoro
        _kok = Kokoro(f"{VOZ_DIR}/kokoro-v1.0.onnx", f"{VOZ_DIR}/voices-v1.0.bin")
    a, sr = _kok.create(texto, voice=VOZ, speed=1.22, lang="pt-br")
    # corta silêncio das pontas
    idx = np.where(np.abs(a) > 0.01)[0]
    if len(idx):
        a = a[max(0, idx[0] - 600): idx[-1] + 1200]
    return a.astype(np.float32)


class Roteiro:
    """Monta a linha do tempo a partir das falas (a voz manda no ritmo)."""
    def __init__(self):
        self.cenas, self.falas, self.t = [], [], 0.35
        self.av_keys = []

    def cena(self, falas, transicao, avatar, montar, cauda=0.35, minimo=0):
        ini = self.t
        ts = []
        for f in falas:
            a = tts(f)
            ts.append(self.t)
            self.falas.append((self.t, a))
            self.t += len(a) / SR_V + 0.12
        fim = max(self.t + cauda, ini + minimo)
        self.t = fim
        c = Cena(ini, fim, transicao)
        montar(c, ts, ini, fim)
        self.cenas.append(c)
        self.av_keys.append((ini, fim, avatar))
        return c

    def voz_total(self, dur):
        v = np.zeros(int(dur * SR_V) + SR_V)
        for t, a in self.falas:
            s = int(t * SR_V)
            v[s:s + len(a)] += a
        return v[: int(dur * SR_V)]


def render(rot, saida):
    cenas = rot.cenas
    cenas[-1].fim += 0.6
    dur = cenas[-1].fim
    voz = rot.voz_total(dur)
    env = envelope(voz, SR_V, FPS, dur)
    ap = Apresentador(env, FPS)
    for i, (ini, fim, (cx, cy, d)) in enumerate(rot.av_keys):
        ap.chave(ini + (0.2 if i else 0), cx, cy, d)
        ap.chave(fim - 0.2, cx, cy, d)
    base = m.fundo_base()
    tmp = saida.replace(".mp4", "_mudo.mp4")
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp],
        stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        t = i / FPS
        fr = m2.compor(cenas, t, base)
        ap.desenhar(fr, t, entrada=0.05)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close(); proc.wait()
    # áudio: trilha baixa + voz + efeitos
    wav = saida.replace(".mp4", ".wav")
    import trilha
    trilha.build(dur, wav)
    with wave.open(wav) as w:
        mus = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32767
    n = len(mus)
    v44 = np.interp(np.arange(n) / 44100, np.arange(len(voz)) / SR_V, voz)
    v44 = v44 / (np.max(np.abs(v44)) + 1e-9) * 0.95
    mix = mus * 0.16 + v44
    rng = np.random.default_rng(1)
    for t, tipo in m2.eventos_som(cenas):
        x = m2.sfx(tipo, rng) * 0.6
        s = int(max(0, t) * 44100)
        e = min(n, s + len(x))
        if s < e:
            mix[s:e] += x[: e - s]
    mix = np.tanh(mix * 1.05) * 0.9
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", saida], check=True)
    os.remove(tmp); os.remove(wav)


def bilhete():
    from PIL import ImageDraw
    w, h = 640, 300
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.rounded_rectangle((0, 0, w - 1, h - 1), radius=40, fill=LIMAO)
    for y in range(30, h - 20, 36):
        g.ellipse((w - 120 - 8, y, w - 120 + 8, y + 16), fill=AZUL)
    g.text((50, 40), "LISTA VIP", font=m.fonte(104, "Black"), fill=VIOLETA)
    g.text((52, 170), "Black Friday 27/11", font=m.fonte(52, "Bold"), fill=AZUL)
    return img


# ---------- posições do avatar ----------
GRANDE = (540, 1250, 500)      # hook
CANTO = (205, 1470, 250)       # story com lista
MEIO = (540, 1330, 380)        # enquete
TOPO = (540, 520, 400)         # offer
CANTO_ALTO = (905, 420, 210)   # scanner


def offer(rot, falas, titulo, t_botao_idx=-1):
    def montar(c, ts, ini, fim):
        y = 520 + 230 + 40
        els, h = palavras(titulo, 92, 920, 80, y, ts[0] + 0.1, alinhar="center")
        c.add(els)
        b = m.sprite_botao("ENTRA NO CANAL", "Canal do WhatsApp • é de graça")
        yb = y + h + 50
        tt = ts[t_botao_idx] + 0.6
        c.add(Apertar(b, (W - b.width) // 2, yb, ts[0] + 0.6, tt))
        c.add(Toque(W // 2 + 330, yb + 125, tt))
        r = m.sprite_texto("link na bio  •  opapaiachou.com.br", 42, 920, peso="SemiBold", cor=LILAS, alinhar="center")
        c.add(Desliza(r, 70, yb + b.height + 40, ts[-1], 0, 60, sfx="pop"))
    return rot.cena(falas, "zoom", TOPO, montar, cauda=0.6)


def lista(c, titulo, itens, ts, t_titulo, icone_tipo, som, y0=340, limite=1300, tam=52):
    els, h = palavras(titulo, 88, 920, 80, y0, t_titulo)
    c.add(els)
    sps = [m.sprite_item(i + 1, txt, tam=tam) for i, txt in enumerate(itens)]
    y = y0 + h + 50
    for s, t in zip(sps, ts):
        c.add(Desliza(s, 80, y, t))
        if icone_tipo:
            c.add(Pop(icone(icone_tipo, 90), 80 + 920 - 66, y - 30, t + 0.4, sfx=som))
        y += s.height + 24
    assert y < limite + 24, f"lista passou do limite: {y}"


# ---------- roteiros ----------
def v01():
    r = Roteiro()

    def hook(c, ts, ini, fim):
        y = gancho_kicker(c, "BLACK FRIDAY SEM CILADA", ini, 340)
        els, h = palavras("Esse desconto é *de verdade* ou é *cilada?*", 92, 920, 80, y, ts[0])
        c.add(els)
        card = cartao_preco("R$ 199,90", "R$ 99,90")
        cy = y + h + 40
        c.add(Desliza(card, 130, cy, ts[0] + 0.5, 0, 220))
        w199 = m.fonte(92, "Bold").getlength("R$ 199,90")
        c.add(Risco(180, cy + 165, 200 + w199, ts[0] + 1.2))
        c.add(Carimbo(carimbo("CILADA?", VERMELHO, 92), 470, cy + 300, fim - 0.9))
    r.cena(["Esse desconto de blék fráidei é de verdade... ou é cilada?"], None, CANTO, hook, cauda=0.9)

    def story1(c, ts, ini, fim):
        k = m.sprite_pilula("PAI DE TRÊS", 44)
        c.add(Pop(k, 80, 400, ts[0]))
        els, h = palavras("Lá em casa *cada real* conta", 112, 920, 80, 500, ts[0] + 0.2)
        c.add(els)
    r.cena(["Lá em casa são três filhos, e cada real conta."], "swipe", GRANDE, story1)

    def story2(c, ts, ini, fim):
        lista(c, "3 sinais de *desconto falso*", [
            "O preço subiu nos dias antes",
            "O preço riscado nunca existiu de verdade",
            "Loja sem avaliação ou com nota baixa"], ts[1:], ts[0], "alerta", "buzz")
    r.cena(["Arrumando as contas, aprendi três sinais de desconto falso.",
            "Um: o preço subiu nos dias antes.",
            "Dois: aquele preço riscado nunca existiu de verdade.",
            "Três: loja sem avaliação, ou com nota baixa."], "swipe", CANTO, story2)

    def enquete(c, ts, ini, fim):
        els, h = palavras("Você já caiu *nessa?*", 116, 920, 80, 380, ts[0], alinhar="center")
        c.add(els)
        yb = 380 + h + 60
        sim, nao = botao_enquete("SIM"), botao_enquete("NÃO")
        c.add(Apertar(sim, 100, yb, ts[0] + 0.4, fim - 0.6, depois=botao_enquete("SIM", cor=AZUL, fundo=LIMAO)),
              Apertar(nao, 560, yb, ts[0] + 0.55, 99))
        c.add(Toque(470, yb + 125, fim - 0.6))
        t = m.sprite_texto("Comenta *SIM* ou *NÃO*", 64, 920, peso="Bold", alinhar="center")
        c.add(Desliza(t, 70, yb + 190, ts[0] + 1.0, 0, 60, sfx="pop"))
    r.cena(["E você, já caiu nessa? Comenta sim ou não."], "flash", MEIO, enquete, cauda=0.9)

    offer(r, ["Por isso eu confiro tudo antes de indicar.",
              "Entra no meu canal do uátsápi e recebe de graça a Lista Vípi da blék fráidei. O link tá na bio!"],
          "O Papai confere *por você*")
    return r


def v02():
    r = Roteiro()

    def hook(c, ts, ini, fim):
        y = gancho_kicker(c, "LISTA VIP BLACK FRIDAY", ini, 340)
        els, h = palavras("Quer os achados *antes de todo mundo?*", 108, 920, 80, y, ts[0])
        c.add(els)
    r.cena(["Quer os achados da blék fráidei antes de todo mundo?"], None, GRANDE, hook, cauda=0.5)

    def story1(c, ts, ini, fim):
        k = m.sprite_pilula("PAI DE TRÊS", 44)
        c.add(Pop(k, 80, 400, ts[0]))
        els, h = palavras("Oferta boa *acaba rápido*", 112, 920, 80, 500, ts[0] + 0.2)
        c.add(els)
        b = bilhete()
        c.add(Pop(b, (W - b.width) // 2 + 120, 900, ts[1] + 0.3, 0.5, 0.2, pulsa=0.02, rot=-25, sfx="ding"))
    r.cena(["Pai de três aprende cedo: oferta boa acaba rápido.", "Por isso eu criei a Lista Vípi."],
           "swipe", CANTO, story1)

    def story2(c, ts, ini, fim):
        lista(c, "Como funciona a *Lista VIP*", [
            "26/11 às 21h: lista prévia só no Canal",
            "27/11: achados das 7h às 22h",
            "Só preço conferido, sem desconto maquiado"], ts, ts[0], "ok", "ding")
    r.cena(["No dia vinte e seis, às nove da noite, sai a lista prévia, só no canal.",
            "No dia vinte e sete, tem achado das sete às dez da noite.",
            "E só entra preço conferido."], "swipe", CANTO, story2)

    def passos(c, ts, ini, fim):
        els, h = palavras("Entrar é *3 toques*", 116, 920, 80, 380, ts[0], alinhar="center")
        c.add(els)
        y = 380 + h + 60
        for txt, t in zip(["1. Link na bio", "2. Entrar no canal", "3. Seguir + sininho"], ts[1:]):
            p = botao_enquete(txt, largura=880)
            c.add(Apertar(p, 100, y, t, t + 0.6, depois=botao_enquete(txt, cor=AZUL, fundo=LIMAO, largura=880)))
            c.add(Toque(930, y + 125, t + 0.6))
            y += p.height + 36
    r.cena(["Pra entrar é fácil.", "Toca no link da bio.", "Entra no canal.", "Segue e ativa o sininho."],
           "flash", (540, 1460, 300), passos)

    offer(r, ["É de graça.", "Te espero lá no canal do uátsápi. Link na bio!"], "Entra no *Canal do Papai*")
    return r


def v03():
    r = Roteiro()

    def hook(c, ts, ini, fim):
        y = gancho_kicker(c, "OS FILTROS DO PAPAI", ini, 340)
        els, h = palavras("Como o Papai *escolhe* um achado?", 116, 920, 80, y, ts[0])
        c.add(els)
    r.cena(["Como o Papai escolhe um achado?"], None, GRANDE, hook, cauda=0.5)

    def story1(c, ts, ini, fim):
        els, h = palavras("Só passa se bater *4 filtros*", 96, 920, 80, 380, ts[0])
        c.add(els)
        y = 380 + h + 70
        for i, (txt, t) in enumerate(zip(["Nota 4,5+", "200+ vendas", "10%+ de desconto", "Original"], ts[1:])):
            p = m.sprite_pilula(txt, 60, pad=(44, 26))
            x = 80 if i % 2 == 0 else 1000 - p.width
            c.add(Pop(p, x, y + (i // 2) * 170, t, 0.35, 0.3, rot=(10 if i % 2 else -10)))
    r.cena(["Eu montei um robô que olha milhares de ofertas por dia, e só passa o que bate quatro filtros:",
            "nota quatro e meio ou mais,", "duzentas vendas ou mais,", "pelo menos dez por cento de desconto,",
            "e produto original."], "swipe", CANTO, story1)

    def teste(c, ts, ini, fim):
        els, h = palavras("Teste do *Papai*", 100, 700, 80, 340, ts[0])
        c.add(els)
        nota = m.sprite_texto("exemplos ilustrativos", 36, 600, peso="Medium", cor=LILAS)
        c.add(Desliza(nota, 80, 340 + h, ts[0] + 0.3, 0, 30, sfx=None))
        y = 340 + h + 90
        casos = [("Garrafa térmica", "nota 4,8", "1.200 vendas", "25% off", "APROVADO", LIMAO, "ding"),
                 ("Fone sem fio", "nota 3,6", "80 vendas", "60% off?!", "REPROVADO", VERMELHO, "buzz"),
                 ("Tênis \"de marca\"", "nota 4,7", "3 mil vendas", "R$ 39 = réplica", "REPROVADO", VERMELHO, "buzz")]
        selos = []
        for (nome, nt, vd, ex, sel, cor, som), t in zip(casos, ts[1:]):
            card = cartao_produto(nome, nt, vd, ex)
            c.add(Desliza(card, 90, y, t - 0.5))
            c.add(Scanner(90, y, 900, 300, t - 0.1, 0.6))
            selos.append(Carimbo(carimbo(sel, cor, 52), 590, y + 185, t + 0.6, sfx=som))
            y += 330
        c.add(selos)
    r.cena(["Olha o teste.", "Essa passou.", "Essa não: nota baixa.", "E essa é réplica. Fora!"],
           "flash", CANTO_ALTO, teste, cauda=0.7)

    offer(r, ["Só o que é aprovado vai pra Lista Vípi.",
              "Entra no meu canal do uátsápi, é de graça. Link na bio!"], "Só o aprovado vai pra *Lista VIP*")
    return r


def v04():
    r = Roteiro()

    def hook(c, ts, ini, fim):
        gancho_kicker(c, "BLACK FRIDAY 27/11", ini, 340)
        c.add(Contador([10, 9, 8, 7], W // 2, 760, ini + 0.1, 0.45))
        els, h = palavras("dias pra *Black Friday*", 100, 920, 80, 1090, ini + 1.5, alinhar="center")
        c.add(els)
    r.cena(["Faltam sete dias pra blék fráidei!"], None, CANTO, hook, cauda=0.8, minimo=2.6)

    def story(c, ts, ini, fim):
        lista(c, "O Papai já está *caçando*", ["Fitness", "Casa e cozinha", "Escola e crianças", "Tecnologia útil"],
              ts[1:], ts[0], None, None)
    r.cena(["E eu já comecei a caçar em quatro frentes:", "fitness,", "casa e cozinha,", "escola e crianças,",
            "e tecnologia útil."], "swipe", CANTO, story)

    def enquete(c, ts, ini, fim):
        els, h = palavras("Qual você quer *primeiro?*", 112, 920, 80, 380, ts[0], alinhar="center")
        c.add(els)
        yb = 380 + h + 60
        for i in range(4):
            b = botao_enquete(str(i + 1), largura=200)
            c.add(Apertar(b, 80 + i * 240, yb, ts[0] + 0.4 + i * 0.12, fim - 0.6 if i == 0 else 99,
                          depois=botao_enquete("1", cor=AZUL, fundo=LIMAO, largura=200) if i == 0 else None))
        c.add(Toque(255, yb + 130, fim - 0.6))
        t = m.sprite_texto("Comenta o *número!*", 72, 920, peso="Black", alinhar="center")
        c.add(Desliza(t, 70, yb + 200, ts[0] + 1.0, 0, 60, sfx="pop"))
    r.cena(["Qual você quer primeiro? Comenta o número!"], "flash", MEIO, enquete, cauda=0.9)

    offer(r, ["Garante seu lugar na Lista Vípi, no meu canal do uátsápi.", "Link na bio!"],
          "Garante seu lugar na *Lista VIP*")
    return r


VIDEOS = {"V01": v01, "V02": v02, "V03": v03, "V04": v04}

if __name__ == "__main__":
    if not sys.argv[1:] or sys.argv[1] == "semana":
        # sem argumentos: lote da semana com ofertas reais (semana.py)
        import semana
        semana.main(sys.argv[2:])
        sys.exit(0)
    for cod in sys.argv[1:]:
        rot = VIDEOS[cod]()
        os.makedirs("saida3", exist_ok=True)
        render(rot, f"saida3/{cod}.mp4")
        print("ok", cod, round(rot.cenas[-1].fim, 1), "s")
