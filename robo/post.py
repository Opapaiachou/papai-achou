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


def texto_canal(oferta):
    """Texto pronto para colar no canal (WhatsApp e Telegram aceitam *negrito* e ~riscado~)."""
    linhas = [f"🔥 *{_limpar_nome(oferta['nome'])}*", ""]
    if oferta.get("preco_antigo"):
        linhas.append(f"De ~{_moeda(oferta['preco_antigo'])}~ por *{_moeda(oferta['preco'])}*{_forma(oferta)}")
    else:
        linhas.append(f"Por *{_moeda(oferta['preco'])}*{_forma(oferta)}")
    if oferta.get("desconto"):
        linhas.append(f"📉 {oferta['desconto']:.0f}% de desconto")
    detalhes = []
    if oferta.get("nota"):
        detalhes.append("⭐ " + f"{oferta['nota']:.1f}".replace(".", ","))
    if oferta.get("vendas"):
        detalhes.append(f"{oferta['vendas']:,}".replace(",", ".") + " vendidos")
    elif oferta.get("avaliacoes"):
        detalhes.append(f"{oferta['avaliacoes']:,}".replace(",", ".") + " avaliações")
    plataforma = oferta.get("plataforma") or "Shopee"
    if plataforma != "Shopee":
        detalhes.append(plataforma)
    elif oferta.get("loja") and oferta["loja"] != "Shopee":
        detalhes.append(oferta["loja"])
    if detalhes:
        linhas.append(" | ".join(detalhes))
    linhas += ["", f"👉 {oferta['link']}", ""]
    if regras.eh_suplemento(oferta["nome"]):
        linhas.append(regras.AVISO_SUPLEMENTO)
    linhas += ["⚠️ Preço pode mudar a qualquer momento", regras.AVISO_AFILIADO]
    return "\n".join(linhas)


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
