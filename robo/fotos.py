"""Guarda uma cópia leve da foto de cada oferta no repositório.

Para o botão "Postar no Canal" mandar foto + texto juntos, o celular precisa baixar a foto.
Algumas lojas (Magalu) não deixam outro site baixar a imagem, então o robô baixa aqui,
diminui (até 800 px, JPEG) e salva em dados/fotos. A Central de Postagem lê pelo
raw.githubusercontent.com, que libera o download para qualquer site.
"""

import hashlib
import io
import os

import requests

PASTA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dados", "fotos")
URL_PUBLICA = "https://raw.githubusercontent.com/Opapaiachou/papai-achou/main/dados/fotos/{arquivo}"
LADO_MAXIMO = 800
CABECALHOS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0 Safari/537.36",
    "Referer": "https://www.magazinevoce.com.br/",
}


def nome_arquivo(chave):
    return hashlib.sha1(str(chave).encode("utf-8")).hexdigest()[:16] + ".jpg"


def garantir(chave, url):
    """Baixa e salva a foto se ainda não existir. Devolve o endereço público ou None se falhar."""
    if not url or not url.startswith("http"):
        return None
    arquivo = nome_arquivo(chave)
    caminho = os.path.join(PASTA, arquivo)
    if not os.path.exists(caminho):
        try:
            from PIL import Image
            resposta = requests.get(url, headers=CABECALHOS, timeout=20)
            resposta.raise_for_status()
            imagem = Image.open(io.BytesIO(resposta.content)).convert("RGB")
            imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            os.makedirs(PASTA, exist_ok=True)
            imagem.save(caminho, "JPEG", quality=85, optimize=True)
        except Exception as erro:  # foto com problema não derruba a rodada
            print(f"Aviso: não consegui guardar a foto de {chave}: {erro}")
            return None
    return URL_PUBLICA.format(arquivo=arquivo)


def limpar(chaves_ativas):
    """Apaga as fotos de ofertas que já saíram da vitrine (o repositório não cresce sem fim)."""
    if not os.path.isdir(PASTA):
        return
    manter = {nome_arquivo(c) for c in chaves_ativas}
    for arquivo in os.listdir(PASTA):
        if arquivo.endswith(".jpg") and arquivo not in manter:
            os.remove(os.path.join(PASTA, arquivo))
