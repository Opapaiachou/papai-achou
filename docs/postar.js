(function () {
  // Central de Postagem: leva as ofertas do robô para o Canal do WhatsApp em 2 toques,
  // pela tela de compartilhar do celular (caminho oficial, sem automação no WhatsApp).
  var CHAVE_FEITOS = "papaiAchouPostados";
  // O WhatsApp não mostra Canais na tela de compartilhar de outros apps. Por isso o botão principal
  // copia o texto, salva a foto no celular e abre o Canal: lá é só anexar a última foto e colar.
  var CANAL = "https://whatsapp.com/channel/0029Vb9k12lICVfgIsD2LN0r";
  var IOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var fotosProntas = {};
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
    if (fotosProntas[o.chave]) return Promise.resolve(fotosProntas[o.chave]);
    return fetch(url, { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("foto");
      return r.blob();
    }).then(function (b) {
      var arq = new File([b], "papai-achou.jpg", { type: b.type && b.type.indexOf("image") === 0 ? b.type : "image/jpeg" });
      fotosProntas[o.chave] = arq;
      return arq;
    }).catch(function () { return null; });
  }

  function abrirCanal() { setTimeout(function () { location.href = CANAL; }, 900); }

  // Botão principal: copia o texto, guarda a foto no celular e abre o Canal.
  function prepararCanal(o, botao) {
    var texto = o.post || o.nome;
    copiar(texto);  // copia já no toque (o celular só deixa copiar durante o toque)
    var pronta = fotosProntas[o.chave];
    if (IOS && pronta && navigator.share && navigator.canShare && navigator.canShare({ files: [pronta] })) {
      // iPhone: abre o compartilhar só com a foto; toque em "Salvar Imagem" e o Canal abre em seguida.
      navigator.share({ files: [pronta] }).then(function () {
        marcar(o, true); aviso("Foto salva e texto copiado. Abrindo o Canal…"); abrirCanal();
      }).catch(function (erro) {
        if (erro && erro.name === "AbortError") return;
        aviso("Texto copiado. Use Baixar foto e depois abra o Canal.");
      });
      return;
    }
    botao.disabled = true; botao.textContent = "Salvando a foto…";
    baixarFoto(o).then(function (arquivo) {
      if (IOS && arquivo) {  // no iPhone o compartilhar precisa de um toque novo depois de baixar
        botao.disabled = false; botao.textContent = "✅ Foto pronta: toque de novo";
        return;
      }
      if (arquivo) {
        var link = document.createElement("a");
        link.href = URL.createObjectURL(arquivo); link.download = "papai-achou-" + Date.now() + ".jpg";
        document.body.appendChild(link); link.click(); link.remove();
        setTimeout(function () { URL.revokeObjectURL(link.href); }, 5000);
      }
      marcar(o, true);
      aviso(arquivo ? "Foto salva e texto copiado. Abrindo o Canal…" : "Texto copiado. Abrindo o Canal…");
      abrirCanal();
    }).finally(function () {
      if (botao.textContent === "Salvando a foto…") { botao.disabled = false; botao.textContent = "📲 Postar no Canal"; }
    });
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
    }).finally(function () { botao.disabled = false; botao.textContent = "Enviar numa conversa"; });
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
    b.addEventListener("click", function () { prepararCanal(o, b); });
    acoes.appendChild(b);
    var z = document.createElement("button"); z.type = "button"; z.className = "botao mini"; z.textContent = "Enviar numa conversa";
    z.addEventListener("click", function () { postar(o, z); });
    acoes.appendChild(z);
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
    if (el) {
      el.classList.add("destaque"); el.scrollIntoView({ block: "center" });
      var o = estado.ofertas.filter(function (x) { return x.chave === alvo; })[0];
      if (o) baixarFoto(o);  // já deixa a foto pronta para o toque
    }
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
