"""Monta o texto da oferta no modelo do canal Papai Achou."""

import html
import re

from robo import regras


def _moeda(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _limpar_nome(nome, limite=90):
    nome = re.sub(r"[【\[].*?[】\]]", "", nome)  # tira [PROMO], 【Pronta entrega】 etc.
    nome = regras.tirar_exageros(nome)  # tira "resultado garantido", "termogênico" etc.
    nome = re.sub(r"\s+", " ", nome).strip(" -|")
    return nome if len(nome) <= limite else nome[: limite - 1].rstrip() + "…"


def texto_canal(oferta):
    """Texto pronto para colar no canal (WhatsApp e Telegram aceitam *negrito* e ~riscado~)."""
    linhas = [f"🔥 *{_limpar_nome(oferta['nome'])}*", ""]
    if oferta.get("preco_antigo"):
        linhas.append(f"De ~{_moeda(oferta['preco_antigo'])}~ por *{_moeda(oferta['preco'])}*")
    else:
        linhas.append(f"Por *{_moeda(oferta['preco'])}*")
    if oferta.get("desconto"):
        linhas.append(f"📉 {oferta['desconto']:.0f}% de desconto")
    detalhes = []
    if oferta.get("nota"):
        detalhes.append("⭐ " + f"{oferta['nota']:.1f}".replace(".", ","))
    if oferta.get("vendas"):
        detalhes.append(f"{oferta['vendas']:,}".replace(",", ".") + " vendidos")
    if oferta.get("loja") and oferta["loja"] != "Shopee":
        detalhes.append(oferta["loja"])
    if detalhes:
        linhas.append(" | ".join(detalhes))
    linhas += ["", f"👉 {oferta['link']}", ""]
    if regras.eh_suplemento(oferta["nome"]):
        linhas.append(regras.AVISO_SUPLEMENTO)
    linhas += ["⚠️ Preço pode mudar a qualquer momento", regras.AVISO_AFILIADO]
    return "\n".join(linhas)


def legenda_aprovacao(oferta, posicao, total):
    """Legenda em HTML para o seu chat privado: o post + os bastidores para você decidir."""
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
    bastidores = (
        f"<b>Oferta {posicao} de {total}</b> · {oferta['pontos']} pontos\n"
        + comissao
        + f"{conferido}\n\n"
        + "<b>Texto para o canal</b> (toque para copiar):\n"
    )
    return bastidores + "<code>" + html.escape(texto_canal(oferta)) + "</code>"
