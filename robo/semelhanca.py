"""Reconhece o mesmo produto anunciado por lojas diferentes, mesmo com nomes escritos de outro jeito."""

import re
import unicodedata

# Palavras que não ajudam a dizer qual é o produto.
VAZIAS = {
    "de", "da", "do", "das", "dos", "com", "sem", "em", "para", "pra", "e", "o", "a", "os", "as", "um", "uma",
    "kit", "novo", "nova", "original", "premium", "promocao", "oferta", "envio", "imediato", "pronta", "entrega",
    "qualidade", "alta", "moderno", "moderna", "lancamento", "top", "super", "mega", "frete", "gratis",
}
SIMILARIDADE_MINIMA = 0.5


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def assinatura(nome):
    """Conjunto de radicais (4 primeiras letras) das palavras que descrevem o produto."""
    palavras = re.findall(r"[a-z]+", _sem_acento(nome.lower()))
    return {p[:4] for p in palavras if len(p) > 2 and p not in VAZIAS}


def parecidos(nome_a, nome_b, minimo=SIMILARIDADE_MINIMA):
    a, b = assinatura(nome_a), assinatura(nome_b)
    if not a or not b:
        return False
    comuns = len(a & b)
    # Compara com o nome mais curto: anúncios longos enchem o título de palavras extras.
    if min(len(a), len(b)) >= 3 and comuns / min(len(a), len(b)) >= 0.7:
        return True
    return comuns / len(a | b) >= minimo


def sem_repetidos(ofertas, ja_vistos=()):
    """Mantém a primeira de cada grupo de produtos parecidos (a lista já deve vir da melhor para a pior)."""
    escolhidas, nomes = [], list(ja_vistos)
    for oferta in ofertas:
        if any(parecidos(oferta["nome"], outro) for outro in nomes):
            continue
        escolhidas.append(oferta)
        nomes.append(oferta["nome"])
    return escolhidas
