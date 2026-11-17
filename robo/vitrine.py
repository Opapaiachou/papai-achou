"""Grava as ofertas escolhidas no arquivo que o site da vitrine lê (docs/ofertas.json)."""

import json
import os
from datetime import datetime, timedelta, timezone

from robo import config, post, semelhanca

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "ofertas.json")
CAMPOS = ("chave", "preco", "preco_antigo", "desconto", "nota", "vendas", "categoria", "loja", "foto", "link")


def _carregar(arquivo):
    if not os.path.exists(arquivo):
        return []
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)


def atualizar(escolhidas, arquivo=ARQUIVO, agora=None):
    agora = agora or datetime.now(timezone.utc)
    novas = []
    for oferta in escolhidas:
        item = {campo: oferta.get(campo) for campo in CAMPOS}
        item["nome"] = post._limpar_nome(oferta["nome"], limite=80)
        item["plataforma"] = "Shopee"
        item["data"] = agora.isoformat()
        novas.append(item)

    chaves_novas = {o["chave"] for o in novas}
    limite = (agora - timedelta(days=config.VITRINE_DIAS)).isoformat()
    antigas = [o for o in _carregar(arquivo) if o.get("chave") not in chaves_novas and o.get("data", "") >= limite]
    lista = semelhanca.sem_repetidos(novas + antigas)[: config.VITRINE_MAXIMO]

    os.makedirs(os.path.dirname(arquivo), exist_ok=True)
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=1)
    return lista
