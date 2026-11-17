"""Histórico de preços e de envios, guardado num arquivo JSON dentro do repositório."""

import json
import os
from datetime import datetime, timedelta, timezone

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "historico.json")


def agora():
    return datetime.now(timezone.utc)


def carregar():
    if not os.path.exists(ARQUIVO):
        return {}
    with open(ARQUIVO, encoding="utf-8") as f:
        return json.load(f)


def salvar(historico):
    os.makedirs(os.path.dirname(ARQUIVO), exist_ok=True)
    # Guarda só os últimos 90 dias de preços de cada produto, para o arquivo não crescer demais.
    limite = (agora() - timedelta(days=90)).isoformat()
    for item in historico.values():
        item["precos"] = [p for p in item["precos"] if p["em"] >= limite]
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=1)


def registrar_preco(historico, chave, nome, preco):
    item = historico.setdefault(chave, {"nome": nome, "precos": [], "enviado_em": None})
    item["nome"] = nome
    item["precos"].append({"em": agora().isoformat(), "preco": preco})
    return item


def menor_preco(item):
    """Menor preço já visto, sem contar a leitura de agora."""
    anteriores = [p["preco"] for p in item["precos"][:-1]]
    return min(anteriores) if anteriores else None


def enviado_recentemente(item, dias):
    if not item.get("enviado_em"):
        return False
    return datetime.fromisoformat(item["enviado_em"]) > agora() - timedelta(days=dias)


def marcar_enviado(historico, chave):
    historico[chave]["enviado_em"] = agora().isoformat()


def nomes_enviados(historico, dias):
    """Nomes dos produtos mandados nos últimos dias, para não mandar o mesmo produto de outra loja."""
    return [item["nome"] for item in historico.values() if enviado_recentemente(item, dias)]
