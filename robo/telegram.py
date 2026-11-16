"""Envio das ofertas para o seu chat privado pelo robô oficial do Telegram."""

import requests

API = "https://api.telegram.org/bot{token}/{metodo}"
LIMITE_LEGENDA = 1024


def _chamar(token, metodo, dados):
    resposta = requests.post(API.format(token=token, metodo=metodo), data=dados, timeout=30)
    corpo = resposta.json()
    if not corpo.get("ok"):
        raise RuntimeError(f"Telegram recusou {metodo}: {corpo.get('description')}")
    return corpo


def enviar_oferta(token, chat_id, foto, legenda):
    """Manda a foto com a legenda. Se a legenda passar do limite, a foto vai sozinha e o texto em seguida."""
    if len(legenda) <= LIMITE_LEGENDA:
        try:
            return _chamar(token, "sendPhoto", {"chat_id": chat_id, "photo": foto, "caption": legenda, "parse_mode": "HTML"})
        except RuntimeError:
            pass  # foto recusada: manda só o texto
    else:
        try:
            _chamar(token, "sendPhoto", {"chat_id": chat_id, "photo": foto})
        except RuntimeError:
            pass
    return _chamar(token, "sendMessage", {"chat_id": chat_id, "text": legenda, "parse_mode": "HTML", "disable_web_page_preview": "false"})


def enviar_texto(token, chat_id, texto):
    return _chamar(token, "sendMessage", {"chat_id": chat_id, "text": texto, "parse_mode": "HTML"})
