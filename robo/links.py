"""Links curtos no domínio do Papai Achou: https://opapaiachou.com.br/o/<código>.

O link de afiliado (Awin, Magalu...) é comprido e assusta quem não conhece. Cada oferta ganha um código
curto e fixo. Quem abre /o/<código> cai na página docs/404.html do site, que procura o código
(primeiro em docs/ofertas.json, depois em dados/links_curtos.json), conta o clique no Google Analytics
e leva a pessoa para o link de afiliado (a comissão continua igual).
Os códigos ficam guardados por DIAS_NO_AR dias depois da última vez que a oferta apareceu.
"""

import hashlib
import html
import json
import os
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(__file__))
REGISTRO = os.path.join(RAIZ, "dados", "links_curtos.json")
SITE = "https://opapaiachou.com.br"
DIAS_NO_AR = 30
ALFABETO = "0123456789abcdefghijklmnopqrstuvwxyz"


def codigo(chave):
    """Código curto e fixo para cada oferta (o mesmo produto sempre ganha o mesmo link)."""
    numero = int(hashlib.sha1(str(chave).encode("utf-8")).hexdigest()[:12], 16)
    texto = ""
    while numero:
        numero, resto = divmod(numero, 36)
        texto = ALFABETO[resto] + texto
    return texto[:7]


def url(oferta):
    return f"{SITE}/o/{codigo(oferta['chave'])}"


def gerar(ofertas, agora=None):
    """Guarda código -> link de afiliado e apaga os que não aparecem há mais de DIAS_NO_AR dias."""
    agora = agora or datetime.now(timezone.utc)
    try:
        with open(REGISTRO, encoding="utf-8") as f:
            registro = json.load(f)
    except (OSError, ValueError):
        registro = {}
    for oferta in ofertas:
        if not oferta.get("chave") or not oferta.get("link"):
            continue
        registro[codigo(oferta["chave"])] = {
            "link": oferta["link"],
            "loja": oferta.get("plataforma") or "Shopee",
            "nome": html.unescape(oferta.get("nome") or "")[:90],
            "preco": oferta.get("preco"),
            "quando": agora.isoformat(),
        }
    limite = (agora - timedelta(days=DIAS_NO_AR)).isoformat()
    registro = {c: d for c, d in registro.items() if d.get("quando", "") >= limite}
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    with open(REGISTRO, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1, sort_keys=True)
    return registro
