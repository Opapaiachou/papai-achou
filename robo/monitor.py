"""Acompanha o preço de produtos cujo feed não informa o "preço de" (ex.: Kabum).

A cada rodada o robô anota o preço do dia de cada produto. Quando o preço de hoje fica
DESCONTO_MINIMO_MONITOR % ou mais abaixo do preço típico dos dias anteriores (a mediana),
o produto vira oferta, com esse preço típico como "de". Assim o desconto é comprovado pelo
nosso próprio histórico, não pelo que a loja diz.
"""

import json
import os
import statistics
from datetime import datetime, timedelta, timezone

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "monitor_precos.json")
DIAS_GUARDADOS = 21
DIAS_MINIMOS = 2              # precisa de pelo menos 2 dias anteriores para comparar
DESCONTO_MINIMO_MONITOR = 10  # % abaixo do preço típico


def _hoje():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d")


def carregar():
    if not os.path.exists(ARQUIVO):
        return {}
    with open(ARQUIVO, encoding="utf-8") as f:
        return json.load(f)


def salvar(dados):
    limite = (datetime.now(timezone.utc) - timedelta(days=DIAS_GUARDADOS)).strftime("%Y-%m-%d")
    for chave in list(dados):
        dados[chave]["p"] = {dia: preco for dia, preco in dados[chave]["p"].items() if dia >= limite}
        if not dados[chave]["p"]:
            del dados[chave]
    os.makedirs(os.path.dirname(ARQUIVO), exist_ok=True)
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))


def registrar(dados, chave, nome, preco):
    """Anota o preço de hoje e devolve o preço típico dos dias anteriores (ou None se ainda não dá para comparar)."""
    item = dados.setdefault(chave, {"n": nome[:80], "p": {}})
    hoje = _hoje()
    anteriores = [p for dia, p in item["p"].items() if dia != hoje]
    item["p"][hoje] = round(preco, 2)
    if len(anteriores) < DIAS_MINIMOS:
        return None
    return statistics.median(anteriores)


def em_queda(preco, tipico):
    """Desconto real em % se o preço de hoje caiu o suficiente; senão None."""
    if not tipico or preco >= tipico:
        return None
    desconto = round((1 - preco / tipico) * 100)
    return desconto if desconto >= DESCONTO_MINIMO_MONITOR else None
