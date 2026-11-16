"""Regras de conteúdo do Papai Achou: o que nunca entra e o que precisa de cuidado no texto.

Base: CONAR (publicidade identificada e sem promessa enganosa), Anvisa (suplemento não é
remédio e não pode prometer cura, emagrecimento ou efeito no corpo) e combate à falsificação.
"""

import re
import unicodedata


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


# Produto reprovado na hora se o nome tiver qualquer um destes termos.
BLOQUEADOS = {
    "falsificação": [r"\breplica\b", r"\bprimeira linha\b", r"\b1a linha\b", r"\bcontratipo\b",
                     r"\binspirad[oa] n[oa]\b", r"\bimportado ab\b", r"\bpremium aaa\b", r"\bnao original\b"],
    "promessa de saúde": [r"\bemagrec", r"\bqueima gordura\b", r"\bseca barriga\b", r"\bperca \d+ ?kg\b",
                          r"\bperde \d+ ?kg\b", r"\bcura\b", r"\bmilagros", r"\bremedio\b",
                          r"\banabolizante", r"\bhormonio", r"\bsibutramina\b", r"\bbomba\b(?! de)",
                          r"\binibidor de apetite\b", r"\btira fome\b"],
    "produto proibido": [r"\bmedicamento\b", r"\bcigarro eletronico\b", r"\bvape\b", r"\bpod descartavel\b",
                         r"\bsoco ingles\b", r"\bsimulacro\b"],
}

# Exageros que saem do nome do produto antes de ir para o post.
EXAGEROS = [r"\bresultado garantido\b", r"\bgarantido\b", r"\b100% eficaz\b", r"\bo melhor do mundo\b",
            r"\bhipertrofia rapida\b", r"\bmassa rapido\b", r"\bdefinicao rapida\b", r"\btermogenico\b"]

# Buscas/termos que indicam suplemento (ganha o aviso obrigatório no texto).
SUPLEMENTOS = [r"\bwhey\b", r"\bcreatina\b", r"\bpre[- ]?treino\b", r"\bproteina\b", r"\bcolageno\b",
               r"\bbcaa\b", r"\bglutamina\b", r"\bmultivitaminico\b", r"\bomega ?3\b",
               r"\bsuplemento\b", r"\bhipercalorico\b"]

AVISO_SUPLEMENTO = "💊 Suplemento não é remédio. Siga a dose do rótulo e, na dúvida, fale com nutricionista ou médico."
AVISO_AFILIADO = "🔗 Link de afiliado: você não paga nada a mais."


def motivo_bloqueio(nome):
    """Devolve o motivo se o produto não pode ser divulgado, ou None se está liberado."""
    texto = _sem_acento(nome)
    for motivo, padroes in BLOQUEADOS.items():
        if any(re.search(p, texto) for p in padroes):
            return motivo
    return None


def eh_suplemento(nome):
    texto = _sem_acento(nome)
    return any(re.search(p, texto) for p in SUPLEMENTOS)


def tirar_exageros(nome):
    """Remove promessas exageradas do nome, mantendo o resto como está."""
    for padrao in EXAGEROS:
        # procura no texto sem acento, mas corta no original pela mesma posição
        while True:
            achado = re.search(padrao, _sem_acento(nome))
            if not achado:
                break
            nome = nome[: achado.start()] + nome[achado.end():]
    return re.sub(r"\s+", " ", nome).strip(" -|,")
