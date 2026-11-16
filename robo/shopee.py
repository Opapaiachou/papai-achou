"""Cliente da API oficial de afiliados da Shopee Brasil (GraphQL assinado)."""

import hashlib
import json
import time

import requests

from robo import config

CONSULTA_OFERTAS = """
query Ofertas($keyword: String, $sortType: Int, $page: Int, $limit: Int) {
  productOfferV2(keyword: $keyword, sortType: $sortType, page: $page, limit: $limit) {
    nodes {
      itemId
      shopId
      productName
      priceMin
      priceMax
      priceDiscountRate
      ratingStar
      sales
      commissionRate
      commission
      imageUrl
      productLink
      offerLink
      shopName
      shopType
    }
    pageInfo { page limit hasNextPage }
  }
}
"""


class ErroShopee(Exception):
    pass


def _assinar(app_id, segredo, corpo):
    """Monta o cabeçalho Authorization: SHA256(AppId + Timestamp + Payload + Secret)."""
    instante = str(int(time.time()))
    assinatura = hashlib.sha256((app_id + instante + corpo + segredo).encode("utf-8")).hexdigest()
    return f"SHA256 Credential={app_id}, Timestamp={instante}, Signature={assinatura}"


def _consultar(app_id, segredo, consulta, variaveis, tentativas=3):
    corpo = json.dumps({"query": consulta, "variables": variaveis}, separators=(",", ":"))
    for tentativa in range(1, tentativas + 1):
        cabecalhos = {
            "Content-Type": "application/json",
            "Authorization": _assinar(app_id, segredo, corpo),
        }
        resposta = requests.post(config.SHOPEE_ENDPOINT, data=corpo, headers=cabecalhos, timeout=30)
        if resposta.status_code in (429, 500, 502, 503, 504) and tentativa < tentativas:
            time.sleep(2 ** tentativa)
            continue
        resposta.raise_for_status()
        dados = resposta.json()
        if dados.get("errors"):
            codigo = dados["errors"][0].get("extensions", {}).get("code")
            if codigo == 10030 and tentativa < tentativas:  # limite de requisições
                time.sleep(2 ** tentativa)
                continue
            raise ErroShopee(json.dumps(dados["errors"], ensure_ascii=False))
        return dados["data"]
    raise ErroShopee("A Shopee não respondeu depois de várias tentativas.")


def buscar_ofertas(app_id, segredo, palavra, limite):
    dados = _consultar(
        app_id,
        segredo,
        CONSULTA_OFERTAS,
        {"keyword": palavra, "sortType": config.SHOPEE_ORDENACAO, "page": 1, "limit": limite},
    )
    return dados["productOfferV2"]["nodes"] or []
