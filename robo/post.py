"""Monta o texto da oferta no modelo do canal Papai Achou."""

import html
import re
from urllib.parse import quote

from robo import regras


def _moeda(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _limpar_nome(nome, limite=90):
    nome = re.sub(r"[【\[].*?[】\]]", "", nome)  # tira [PROMO], 【Pronta entrega】 etc.
    nome = regras.tirar_exageros(nome)  # tira "resultado garantido", "termogênico" etc.
    nome = re.sub(r"\s+", " ", nome).strip(" -|")
    return nome if len(nome) <= limite else nome[: limite - 1].rstrip() + "…"


def _forma(oferta):
    """' no Pix' quando o preço mostrado é o do Pix (Magalu/Mercado Livre)."""
    forma = (oferta.get("forma_preco") or "").strip()
    return f" {forma}" if forma.lower().startswith("no ") else ""


# Onde a oferta está, no fim do post (como "Agora, na Amazon!").
ONDE = {"Magalu": "Agora, no Magalu!", "Mercado Livre": "Agora, no Mercado Livre!", "Shopee": "Agora, na Shopee!",
        "Amazon": "Agora, na Amazon!", "Kabum": "Agora, na KaBuM!", "KaBuM": "Agora, na KaBuM!",
        "Dafiti": "Agora, na Dafiti!"}
# /zap leva ao site com utm_source=whatsapp (docs/zap/index.html), para o Analytics contar o Canal.
CHAMADA_SITE = "🛍️ Para mais ofertas acesse o site: www.opapaiachou.com.br/zap"


def _moeda_curta(valor):
    """R$159 ou R$252,97 (sem espaço e sem ,00, como nos canais de ofertas)."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$" + (texto[:-3] if texto.endswith(",00") else texto)


def _nome_curto(nome, limite=60):
    """Nome direto: sem código HTML, sem ™/®, cortado numa vírgula ou palavra inteira."""
    nome = _limpar_nome(html.unescape(nome or ""), limite=200).replace("™", "").replace("®", "").rstrip("…").strip()
    if len(nome) <= limite:
        return nome
    corte = max(nome.rfind(", ", 0, limite), nome.rfind(" - ", 0, limite))
    if corte >= 25:
        return nome[:corte].strip()
    return nome[:limite].rsplit(" ", 1)[0].rstrip(" ,-|")


def texto_canal(oferta):
    """Post no padrão dos canais de ofertas (WhatsApp e Telegram aceitam *negrito*, _itálico_ e ~riscado~)."""
    linhas = []
    desconto = oferta.get("desconto") or 0
    if desconto >= 40:
        linhas += [f"🚨 *{desconto:.0f}% OFF!*", ""]
    linhas += [f"*{_nome_curto(oferta['nome'])}*", ""]
    if oferta.get("preco_antigo"):
        linhas.append(f"De ~{_moeda_curta(oferta['preco_antigo'])}~")
    linhas += [f"Por *{_moeda_curta(oferta['preco'])}* 🔥{_forma(oferta)}", ""]
    linhas += ["👉 *Pegar promoção:*", oferta["link"], ""]
    plataforma = oferta.get("plataforma") or "Shopee"
    linhas.append(ONDE.get(plataforma, f"Loja oficial {plataforma}!"))
    if regras.eh_suplemento(oferta["nome"]):
        linhas += ["", regras.AVISO_SUPLEMENTO]
    linhas += ["", "_🔗 Link de afiliado · o preço pode mudar a qualquer momento_", "", CHAMADA_SITE]
    return "\n".join(linhas)


# Link do site marcado como vindo do WhatsApp (aparece assim no Google Analytics).
SITE_WHATSAPP = "https://opapaiachou.com.br/?utm_source=whatsapp&utm_medium=canal"


def link_whatsapp(texto):
    """Link oficial do WhatsApp que abre o app com o texto pronto (você escolhe o Canal e envia)."""
    return "https://wa.me/?text=" + quote(texto, safe="")


def link_central(chave):
    """Central de Postagem já aberta na oferta: o botão de lá compartilha foto + texto no WhatsApp."""
    return f"{CENTRAL}#{quote(chave, safe='')}"


CENTRAL = "https://opapaiachou.com.br/postar.html"


def legenda_aprovacao(oferta, posicao, total):
    """Bastidores em HTML, só para você: comissão, pontos e se o preço já foi conferido."""
    if oferta.get("preco_conferido"):
        conferido = f"✅ Menor preço já visto: {_moeda(oferta['menor_preco_visto'])}"
    else:
        conferido = "🆕 Primeira vez que o robô vê este produto: confira o histórico antes"
    comissao = ""
    if oferta.get("comissao_taxa"):
        comissao = f"💰 Comissão: {oferta['comissao_taxa'] * 100:.0f}%"
        if oferta.get("comissao_valor"):
            comissao += f" (≈ {_moeda(oferta['comissao_valor'])} por venda)"
        comissao += "\n"
    return (
        f"🔒 <b>Oferta {posicao} de {total}</b> · {oferta.get('plataforma') or 'Shopee'} · {oferta['pontos']} pontos · só para você\n"
        + comissao
        + f"{conferido}\n"
        + f"📲 Postar no Canal em 2 toques: {CENTRAL}#{quote(str(oferta.get('chave', '')), safe='')}\n"
        + "⬇️ Post pronto para o WhatsApp logo abaixo"
    )


INSTRUCOES_WHATSAPP = (
    "📲 <b>Como postar no Canal do WhatsApp</b>\n"
    "1. Na oferta que quiser, segure a foto e toque em <b>Salvar</b> (vai para a galeria).\n"
    "2. Segure a mesma mensagem e toque em <b>Copiar</b> (copia o texto).\n"
    "3. No WhatsApp, abra o Canal Papai Achou, anexe a foto da galeria e cole o texto como legenda.\n"
    "Os *asteriscos* e ~tis~ viram <b>negrito</b> e riscado no WhatsApp."
)
