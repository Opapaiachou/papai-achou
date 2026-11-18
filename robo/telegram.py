"""Envio das ofertas para o seu chat privado pelo robô oficial do Telegram."""

import time

import requests

API = "https://api.telegram.org/bot{token}/{metodo}"
LIMITE_LEGENDA = 1024


def _chamar(token, metodo, dados, tentativas=3):
    """Chama a API do Telegram. Se ele demorar ou cair, tenta de novo antes de desistir."""
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.post(API.format(token=token, metodo=metodo), data=dados, timeout=60)
            corpo = resposta.json()
        except (requests.RequestException, ValueError) as erro:
            if tentativa == tentativas:
                raise RuntimeError(f"Telegram não respondeu a {metodo}: {erro}")
            time.sleep(5 * tentativa)
            continue
        if corpo.get("ok"):
            return corpo
        espera = (corpo.get("parameters") or {}).get("retry_after")
        if espera and tentativa < tentativas:  # limite de mensagens: espera o que o Telegram pedir
            time.sleep(int(espera) + 1)
            continue
        raise RuntimeError(f"Telegram recusou {metodo}: {corpo.get('description')}")


def enviar_post(token, chat_id, foto, texto):
    """Foto + texto puro (sem HTML), para copiar e colar no WhatsApp com os *asteriscos* intactos."""
    if foto and len(texto) <= LIMITE_LEGENDA:
        try:
            return _chamar(token, "sendPhoto", {"chat_id": chat_id, "photo": foto, "caption": texto})
        except RuntimeError:
            pass
    elif foto:
        try:
            _chamar(token, "sendPhoto", {"chat_id": chat_id, "photo": foto})
        except RuntimeError:
            pass
    return _chamar(token, "sendMessage", {"chat_id": chat_id, "text": texto})


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
