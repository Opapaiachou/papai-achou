"""Rodada do robô Papai Achou: busca, filtra, monta os posts e manda para você aprovar.

Uso:
  python -m robo.main                 rodada de verdade (precisa das chaves nas variáveis de ambiente)
  python -m robo.main --demo          testa com produtos de exemplo e mostra os posts na tela
  python -m robo.main --planilha      lê as planilhas da pasta "entrada" (links gerados no painel da Shopee)
  python -m robo.main --teste         manda os produtos de exemplo para o seu Telegram (testa o robô sem a Shopee)
  python -m robo.main --chat-id       mostra o seu chat_id depois que você mandar /start ao robô
"""

import json
import os
import sys

import requests

from robo import config, curadoria, historico, planilha, post, shopee, telegram, vitrine

PASTA = os.path.dirname(os.path.dirname(__file__))


def _variavel(nome):
    valor = os.environ.get(nome, "").strip()
    if not valor:
        sys.exit(f"Falta a variável {nome}. Veja o passo a passo no README.")
    return valor


def coletar_reais():
    app_id, segredo = _variavel("SHOPEE_APP_ID"), _variavel("SHOPEE_SECRET")
    nos = []
    for palavra, categoria in config.PALAVRAS_CHAVE.items():
        try:
            achados = shopee.buscar_ofertas(app_id, segredo, palavra, config.PRODUTOS_POR_PALAVRA)
            for no in achados:
                no["_categoria"] = categoria
            nos += achados
        except Exception as erro:  # uma palavra com problema não derruba a rodada
            print(f"Aviso: falha ao buscar '{palavra}': {erro}")
    return nos


def coletar_exemplo():
    with open(os.path.join(PASTA, "exemplos", "ofertas_exemplo.json"), encoding="utf-8") as f:
        return json.load(f)


def _enviar(token, chat_id, oferta, posicao, total):
    """Duas mensagens: os bastidores (só para você) e o post pronto para o canal."""
    telegram.enviar_texto(token, chat_id, post.legenda_aprovacao(oferta, posicao, total))
    telegram.enviar_post(token, chat_id, oferta["foto"], post.texto_canal(oferta))


def rodada(demo=False, teste=False, de_planilha=False):
    hist = {} if (demo or teste) else historico.carregar()
    if demo or teste:
        nos = coletar_exemplo()
    elif de_planilha:
        nos = planilha.coletar()
        if not nos:
            print("Nenhuma planilha nova na pasta entrada.")
            return []
    else:
        nos = coletar_reais()
    aprovadas = curadoria.escolher(nos, hist)
    escolhidas = curadoria.misturar_categorias(aprovadas)[: config.OFERTAS_POR_RODADA]
    da_vitrine = curadoria.misturar_categorias(aprovadas)[: config.VITRINE_POR_RODADA]
    print(f"{len(nos)} produtos analisados, {len(aprovadas)} aprovados, {len(escolhidas)} para o Telegram, {len(da_vitrine)} para a vitrine.")

    if demo:
        barrados = {}
        for no in nos:
            motivo = curadoria.motivo_reprovacao(curadoria.normalizar(no))
            if motivo:
                barrados.setdefault(motivo, []).append(no.get("productName", ""))
        for motivo, nomes in barrados.items():
            print(f"Barrados por {motivo}: " + "; ".join(nomes))
        for i, oferta in enumerate(escolhidas, 1):
            print(f"\n----- Oferta {i} ({oferta['pontos']} pontos) -----")
            print(post.texto_canal(oferta))
        return escolhidas

    token, chat_id = _variavel("TELEGRAM_TOKEN"), _variavel("TELEGRAM_CHAT_ID")
    if teste:
        telegram.enviar_texto(token, chat_id, "🧪 <b>Teste do robô Papai Achou</b>\nProdutos de exemplo, links falsos. Se você está lendo isto, o envio está funcionando.")
        telegram.enviar_texto(token, chat_id, post.INSTRUCOES_WHATSAPP)
        for i, oferta in enumerate(escolhidas, 1):
            _enviar(token, chat_id, oferta, i, len(escolhidas))
        print("Teste enviado para o Telegram.")
        return escolhidas
    if not escolhidas:
        telegram.enviar_texto(token, chat_id, "🔎 Rodada sem ofertas que passaram no filtro. Tento de novo na próxima.")
    elif de_planilha:
        telegram.enviar_texto(token, chat_id, post.INSTRUCOES_WHATSAPP)
    for i, oferta in enumerate(escolhidas, 1):
        _enviar(token, chat_id, oferta, i, len(escolhidas))
        historico.marcar_enviado(hist, oferta["chave"])
    historico.salvar(hist)
    vitrine.atualizar(da_vitrine)
    if de_planilha:
        planilha.arquivar()
    return escolhidas


def mostrar_chat_id():
    token = _variavel("TELEGRAM_TOKEN")
    dados = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30).json()
    if not dados.get("ok"):
        sys.exit(f"O Telegram recusou o token ({dados.get('description')}). Confira o segredo TELEGRAM_TOKEN.")
    chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "") for u in dados.get("result", []) if "message" in u}
    if not chats:
        print("Nenhuma mensagem encontrada. Abra o seu robô no Telegram, mande /start e rode de novo.")
    for chat_id, nome in chats.items():
        print(f"chat_id de {nome}: {chat_id}")


if __name__ == "__main__":
    if "--chat-id" in sys.argv:
        mostrar_chat_id()
    else:
        rodada(demo="--demo" in sys.argv, teste="--teste" in sys.argv, de_planilha="--planilha" in sys.argv)
