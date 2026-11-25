(function () {
  // Central de Postagem: leva as ofertas do robô para o Canal do WhatsApp em 2 toques,
  // pela tela de compartilhar do celular (caminho oficial, sem automação no WhatsApp).
  var CHAVE_FEITOS = "papaiAchouPostados";
  var feitos = {};
  try { feitos = JSON.parse(localStorage.getItem(CHAVE_FEITOS) || "{}"); } catch (e) { feitos = {}; }
  var estado = { ofertas: [], filtro: "pendentes" };
  var lista = document.getElementById("lista");
  var chips = document.getElementById("chips");
  var contagem = document.getElementById("contagem");

  function salvarFeitos() { try { localStorage.setItem(CHAVE_FEITOS, JSON.stringify(feitos)); } catch (e) {} }
  function moeda(v) { return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
  function aviso(texto) {
    var t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); t.textContent = texto;
    document.body.appendChild(t); setTimeout(function () { t.remove(); }, 3500);
  }
  function copiar(texto) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(texto).catch(function () {});
    var ta = document.createElement("textarea"); ta.value = texto; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {} ta.remove(); return Promise.resolve();
  }
  function marcar(o, valor) {
    if (valor) feitos[o.chave] = new Date().toISOString(); else delete feitos[o.chave];
    salvarFeitos(); desenhar();
  }

  function baixarFoto(o) {
    var url = o.foto_post || o.foto;
    if (!url) return Promise.resolve(null);
    return fetch(url, { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("foto");
      return r.blob();
    }).then(function (b) {
      return new File([b], "papai-achou.jpg", { type: b.type && b.type.indexOf("image") === 0 ? b.type : "image/jpeg" });
    }).catch(function () { return null; });
  }

  function postar(o, botao) {
    var texto = o.post || o.nome;
    copiar(texto); // segurança: se o WhatsApp não puxar a legenda, é só colar
    botao.disabled = true; botao.textContent = "Preparando…";
    baixarFoto(o).then(function (arquivo) {
      var dados = { text: texto };
      if (arquivo && navigator.canShare && navigator.canShare({ files: [arquivo] })) dados.files = [arquivo];
      if (!navigator.share) {
        aviso("Texto copiado. Neste aparelho não dá para compartilhar direto: use Baixar foto.");
        return;
      }
      return navigator.share(dados).then(function () {
        marcar(o, true); aviso("Enviado! Marcado como postado.");
      }).catch(function (erro) {
        if (erro && erro.name === "AbortError") return;
        aviso("Não abriu o compartilhar. O texto já está copiado.");
      });
    }).finally(function () { botao.disabled = false; botao.textContent = "📲 Postar no Canal"; });
  }

  function cartao(o) {
    var li = document.createElement("li"); li.className = "post" + (feitos[o.chave] ? " feito" : "");
    li.id = "o-" + encodeURIComponent(o.chave);
    var foto = document.createElement("div"); foto.className = "foto";
    var img = document.createElement("img"); img.src = o.foto_post || o.foto; img.alt = ""; img.loading = "lazy";
    foto.appendChild(img);
    var tag = document.createElement("span"); tag.className = "loja-tag"; tag.textContent = o.plataforma || "Shopee"; foto.appendChild(tag);
    li.appendChild(foto);

    var corpo = document.createElement("div"); corpo.className = "corpo";
    var h2 = document.createElement("h2"); h2.textContent = o.nome; corpo.appendChild(h2);
    var linha = document.createElement("div"); linha.className = "linha";
    if (o.preco_antigo) { var ant = document.createElement("span"); ant.className = "antigo"; ant.textContent = moeda(o.preco_antigo); linha.appendChild(ant); }
    var atual = document.createElement("span"); atual.className = "atual"; atual.textContent = moeda(o.preco); linha.appendChild(atual);
    if (o.desconto) { var d = document.createElement("span"); d.textContent = "-" + Math.round(o.desconto) + "%"; linha.appendChild(d); }
    corpo.appendChild(linha);
    if (feitos[o.chave]) { var e = document.createElement("span"); e.className = "estado"; e.textContent = "✓ Postado"; corpo.appendChild(e); }

    var acoes = document.createElement("div"); acoes.className = "acoes";
    var b = document.createElement("button"); b.type = "button"; b.className = "botao principal"; b.textContent = "📲 Postar no Canal";
    b.addEventListener("click", function () { postar(o, b); });
    acoes.appendChild(b);
    var c = document.createElement("button"); c.type = "button"; c.className = "botao mini"; c.textContent = "Copiar texto";
    c.addEventListener("click", function () { copiar(o.post || o.nome).then(function () { aviso("Texto copiado."); }); });
    acoes.appendChild(c);
    var f = document.createElement("a"); f.className = "botao mini"; f.textContent = "Baixar foto";
    f.href = o.foto_post || o.foto; f.download = "papai-achou.jpg"; f.target = "_blank"; f.rel = "noopener";
    acoes.appendChild(f);
    var m = document.createElement("button"); m.type = "button"; m.className = "botao mini";
    m.textContent = feitos[o.chave] ? "Desmarcar" : "Já postei";
    m.addEventListener("click", function () { marcar(o, !feitos[o.chave]); });
    acoes.appendChild(m);
    corpo.appendChild(acoes);
    li.appendChild(corpo);
    return li;
  }

  var FILTROS = [["pendentes", "Para postar"], ["todas", "Todas"], ["Magalu", "Magalu"], ["Mercado Livre", "Mercado Livre"], ["Shopee", "Shopee"]];
  FILTROS.forEach(function (par) {
    var bt = document.createElement("button"); bt.type = "button"; bt.className = "chip"; bt.textContent = par[1];
    bt.setAttribute("aria-pressed", par[0] === estado.filtro ? "true" : "false");
    bt.addEventListener("click", function () {
      estado.filtro = par[0];
      chips.querySelectorAll(".chip").forEach(function (x) { x.setAttribute("aria-pressed", x === bt ? "true" : "false"); });
      desenhar();
    });
    chips.appendChild(bt);
  });

  function desenhar() {
    var itens = estado.ofertas.filter(function (o) {
      if (estado.filtro === "pendentes") return !feitos[o.chave];
      if (estado.filtro === "todas") return true;
      return (o.plataforma || "Shopee") === estado.filtro;
    });
    contagem.textContent = itens.length + (itens.length === 1 ? " oferta" : " ofertas") +
      " · " + Object.keys(feitos).length + " já postadas neste celular";
    lista.innerHTML = "";
    itens.forEach(function (o) { lista.appendChild(cartao(o)); });
    destacar();
  }

  function destacar() {
    var alvo = decodeURIComponent((location.hash || "").slice(1));
    if (!alvo) return;
    var el = document.getElementById("o-" + encodeURIComponent(alvo));
    if (!el && estado.filtro !== "todas") { estado.filtro = "todas"; return desenhar(); }
    if (el) { el.classList.add("destaque"); el.scrollIntoView({ block: "center" }); }
    else if (estado.ofertas.length && !destacar.avisou) {
      destacar.avisou = true;  // o robô manda no Telegram antes de o site atualizar (leva 1 a 2 minutos)
      aviso("Essa oferta ainda está chegando no site. Atualize a página em 2 minutinhos.");
    }
  }
  window.addEventListener("hashchange", desenhar);

  fetch("ofertas.json", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (dados) {
    estado.ofertas = (dados || []).sort(function (a, b) { return (b.data || "").localeCompare(a.data || ""); });
    desenhar();
  }).catch(function () { contagem.textContent = "Não consegui carregar as ofertas. Tente de novo em instantes."; });
})();
