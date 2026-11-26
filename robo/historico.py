"""Histórico de preços e de envios, guardado num arquivo JSON dentro do repositório."""

import json
import os
from datetime import datetime, timedelta, timezone

BRASILIA = timezone(timedelta(hours=-3))
DIAS_GUARDADOS = 90       # dias de preços guardados por produto
DIAS_SEM_VER = 30         # produto que não aparece há mais que isso sai do histórico

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "historico.json")


def agora():
    return datetime.now(timezone.utc)


def carregar():
    if not os.path.exists(ARQUIVO):
        return {}
    with open(ARQUIVO, encoding="utf-8") as f:
        return json.load(f)


def _dia(instante):
    """Dia (horário de Brasília) de uma leitura: '2026-11-26'."""
    return datetime.fromisoformat(instante).astimezone(BRASILIA).strftime("%Y-%m-%d")


def _um_por_dia(precos):
    """Junta as leituras do mesmo dia numa só, com o menor preço do dia (o arquivo para de inchar)."""
    dias = {}
    for p in precos:
        dia = _dia(p["em"])
        if dia not in dias or p["preco"] < dias[dia]["preco"]:
            dias[dia] = {"em": p["em"], "preco": p["preco"]}
    return [dias[d] for d in sorted(dias)]


def salvar(historico):
    os.makedirs(os.path.dirname(ARQUIVO), exist_ok=True)
    # Guarda um preço por dia, só dos últimos 90 dias, e esquece produtos que sumiram há 30 dias
    # (a não ser que tenham sido mandados no Telegram há pouco, para não repetir).
    limite = (agora() - timedelta(days=DIAS_GUARDADOS)).isoformat()
    sumiu = (agora() - timedelta(days=DIAS_SEM_VER)).isoformat()
    for chave in list(historico):
        item = historico[chave]
        item["precos"] = _um_por_dia([p for p in item["precos"] if p["em"] >= limite])
        ultimo = item["precos"][-1]["em"] if item["precos"] else ""
        if ultimo < sumiu and (item.get("enviado_em") or "") < sumiu:
            del historico[chave]
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, separators=(",", ":"))


def registrar_preco(historico, chave, nome, preco):
    item = historico.setdefault(chave, {"nome": nome, "precos": [], "enviado_em": None})
    item["nome"] = nome
    item["precos"].append({"em": agora().isoformat(), "preco": preco})
    return item


def menor_preco(item):
    """Menor preço visto nos dias anteriores (as leituras de hoje não contam)."""
    hoje = agora().astimezone(BRASILIA).strftime("%Y-%m-%d")
    anteriores = [p["preco"] for p in item["precos"] if _dia(p["em"]) != hoje]
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
