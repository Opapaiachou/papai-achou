"""Grava as ofertas escolhidas no arquivo que o site da vitrine lê (docs/ofertas.json)."""

import json
import os
from datetime import datetime, timedelta, timezone

from robo import awin, config, curadoria, fotos, post, semelhanca

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "ofertas.json")
CAMPOS = ("chave", "preco", "preco_antigo", "desconto", "nota", "vendas", "avaliacoes", "forma_preco", "categoria", "loja",
          "foto", "link")


def _carregar(arquivo):
    if not os.path.exists(arquivo):
        return []
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)


def _revisar_antiga(item):
    """Aplica as regras atuais aos achados que já estavam no site. Devolve None se não vale mais."""
    if "awin1.com" in (item.get("link") or ""):
        if (item.get("desconto") or 0) > awin.DESCONTO_MAXIMO_AWIN:
            return None  # desconto inflado: sai do site
        item["categoria"] = curadoria.categoria_final(item.get("nome"), awin.categoria_de(item.get("nome")) or item.get("categoria"))
    else:
        item["categoria"] = curadoria.categoria_final(item.get("nome"), item.get("categoria"))
    return item


def atualizar(escolhidas, arquivo=ARQUIVO, agora=None):
    agora = agora or datetime.now(timezone.utc)
    novas = []
    for oferta in escolhidas:
        item = {campo: oferta.get(campo) for campo in CAMPOS}
        item["nome"] = post._limpar_nome(oferta["nome"], limite=80)
        item["plataforma"] = oferta.get("plataforma") or "Shopee"
        item["data"] = agora.isoformat()
        item["post"] = post.texto_canal(oferta)  # texto pronto para o Canal do WhatsApp
        novas.append(item)

    chaves_novas = {o["chave"] for o in novas}
    limite = (agora - timedelta(days=config.VITRINE_DIAS)).isoformat()
    antigas = [o for o in _carregar(arquivo) if o.get("chave") not in chaves_novas and o.get("data", "") >= limite]
    antigas = [o for o in map(_revisar_antiga, antigas) if o]
    lista = semelhanca.sem_repetidos(novas + antigas)[: config.VITRINE_MAXIMO]

    # Central de Postagem: cada oferta com o post pronto e uma foto que o celular consegue baixar.
    for item in lista:
        if not item.get("post"):
            item["post"] = post.texto_canal(item)
        if not item.get("foto_post"):
            item["foto_post"] = fotos.garantir(item["chave"], item.get("foto"))
    fotos.limpar(o["chave"] for o in lista)

    os.makedirs(os.path.dirname(arquivo), exist_ok=True)
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    return lista
