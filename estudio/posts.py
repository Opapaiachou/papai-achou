"""Carrosséis 1080x1350 do Papai Achou."""
import os
from PIL import Image, ImageDraw, ImageFilter
import motor as m

PW, PH = 1080, 1350


def fundo(n, total):
    img = Image.new("RGBA", (PW, PH), m.AZUL + (255,))
    glow = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((-400, -400, 800, 700), fill=m.VIOLETA + (150,))
    g.ellipse((600, 900, 1500, 1800), fill=m.VIOLETA + (110,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(200)))
    d = ImageDraw.Draw(img)
    for y in range(40, PH, 60):
        for x in range(40, PW, 60):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255, 28))
    img.alpha_composite(m.sprite_mascote(80, anel=False), (70, 64))
    d.text((168, 66), "Papai Achou", font=m.fonte(40, "Black"), fill=m.BRANCO)
    d.text((168, 112), "@opapaiachou", font=m.fonte(28, "Medium"), fill=m.LILAS)
    # paginação
    f = m.fonte(30, "SemiBold")
    txt = f"{n}/{total}"
    d.text((PW - 70 - f.getlength(txt), 88), txt, font=f, fill=m.LILAS)
    return img


def capa(n, total, kicker, titulo, sub):
    img = fundo(n, total)
    k = m.sprite_pilula(kicker, 38)
    img.alpha_composite(k, (80, 260))
    t = m.sprite_texto(titulo, 124, 920)
    img.alpha_composite(t, (70, 350))
    s = m.sprite_texto(sub, 50, 900, peso="SemiBold", cor=m.LILAS)
    y = 350 + t.height + 20
    img.alpha_composite(s, (70, y))
    mas = m.sprite_mascote(300)
    img.alpha_composite(mas, (PW - mas.width - 60, PH - mas.height - 60))
    a = m.sprite_pilula("arrasta pro lado  >", 36, fundo=m.VIOLETA, cor=m.BRANCO, peso="Bold")
    img.alpha_composite(a, (80, PH - a.height - 100))
    return img


def passo(n, total, num, titulo, texto):
    img = fundo(n, total)
    d = ImageDraw.Draw(img)
    cx, cy, r = 150, 400, 80
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=m.LIMAO)
    fn = m.fonte(100, "Black")
    asc, desc = fn.getmetrics()
    d.text((cx - fn.getlength(str(num)) / 2, cy - (asc + desc) / 2 - 4), str(num), font=fn, fill=m.AZUL)
    t = m.sprite_texto(titulo, 96, 920)
    img.alpha_composite(t, (70, 530))
    card_y = 530 + t.height + 40
    corpo = m.sprite_texto(texto, 56, 820, peso="Medium", entrelinha=1.25)
    ch = corpo.height + 80
    d.rounded_rectangle((80, card_y, PW - 80, card_y + ch), radius=40, fill=m.AZUL_CARD, outline=m.VIOLETA, width=4)
    img.alpha_composite(corpo, (110, card_y + 30))
    mas = m.sprite_mascote(200)
    img.alpha_composite(mas, (PW - mas.width - 70, 270))
    return img


def cta(n, total, titulo, botao, sub, rodape="link na bio  •  opapaiachou.com.br"):
    img = fundo(n, total)
    mas = m.sprite_mascote(320)
    img.alpha_composite(mas, ((PW - mas.width) // 2, 200))
    t = m.sprite_texto(titulo, 84, 920, alinhar="center")
    y = 200 + mas.height + 40
    img.alpha_composite(t, (70, y))
    b = m.sprite_botao(botao, sub)
    y += t.height + 40
    img.alpha_composite(b, ((PW - b.width) // 2, y))
    r = m.sprite_texto(rodape, 40, 920, peso="SemiBold", cor=m.LILAS, alinhar="center")
    img.alpha_composite(r, (70, y + b.height + 30))
    return img


def salvar(slides, pasta):
    os.makedirs(pasta, exist_ok=True)
    for i, s in enumerate(slides, 1):
        s.convert("RGB").save(os.path.join(pasta, f"{i:02d}.jpg"), quality=92)


if __name__ == "__main__":
    T = 7
    salvar([
        capa(1, T, "BLACK FRIDAY 27/11", "Checklist *anti-cilada*", "5 coisas pra conferir antes de pagar"),
        passo(2, T, 1, "Histórico de *preço*", "Veja se o preço subiu nos dias antes. Desconto em cima de preço inflado não é desconto."),
        passo(3, T, 2, "Nota e *vendas*", "Nota 4,5 ou mais e muitas vendas. Leia as avaliações com foto de quem já comprou."),
        passo(4, T, 3, "Preço final no *carrinho*", "Frete, cupom e parcelamento mudam o preço. Compare o total, não o preço da vitrine."),
        passo(5, T, 4, "Produto *original*", "Desconfie de marca famosa com preço bom demais. Réplica não é achado."),
        passo(6, T, 5, "Compra com *lista*", "Monte sua lista antes do dia 27. Compre o que você precisa, não o que tem cronômetro."),
        cta(7, T, "O Papai faz esse checklist *por você*", "LISTA VIP", "no Canal do WhatsApp • é de graça"),
    ], "saida/post_19-11")
    T = 5
    salvar([
        capa(1, T, "LISTA VIP BLACK FRIDAY", "Como entrar na *Lista VIP*", "3 passos, menos de 1 minuto"),
        passo(2, T, 1, "Toque no *link da bio*", "Ele abre o site do Papai: opapaiachou.com.br"),
        passo(3, T, 2, "Entre no *Canal*", "Toque em \"Entrar no canal do WhatsApp\" e depois em \"Seguir\"."),
        passo(4, T, 3, "Ative o *sininho*", "Canal do WhatsApp vem silenciado. Ative as notificações para receber a lista na hora."),
        cta(5, T, "26/11 às 21h: lista prévia *só no Canal*", "ENTRA NO CANAL", "Canal do WhatsApp • é de graça"),
    ], "saida/post_20-11")
    print("ok")
