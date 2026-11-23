(function () {
  var CATEGORIAS = ["Todos", "Fitness", "Casa e cozinha", "Escola", "Crianças", "Moda", "Maquiagem e beleza", "Tecnologia útil", "Presentes"];
  var pagina = document.body.getAttribute("data-pagina");
  var cfg = window.PAPAI_ACHOU || {};
  var estado = { ofertas: [], categoria: "Todos", busca: "" };

  // Links das redes (vêm do config.js)
  document.querySelectorAll("[data-link]").forEach(function (a) {
    var url = cfg[a.getAttribute("data-link")];
    if (url && url !== "#") { a.href = url; a.target = "_blank"; a.rel = "noopener"; }
  });
  var ano = document.getElementById("ano");
  if (ano) ano.textContent = new Date().getFullYear();

  if (pagina === "black-friday") iniciarContagem();
  if (pagina !== "inicio" && pagina !== "black-friday") return;

  var grade = document.getElementById("grade");
  var contagem = document.getElementById("contagem");
  var chips = document.getElementById("chips");
  var busca = document.getElementById("busca");

  function semAcento(t) { return (t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  function moeda(v) { return Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
  function dataCurta(iso) {
    var d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso + "T12:00:00" : iso);
    return isNaN(d) ? "" : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  }

  function lerCSV(texto) {
    var linhas = [], linha = [], campo = "", aspas = false;
    for (var i = 0; i < texto.length; i++) {
      var c = texto[i];
      if (aspas) {
        if (c === '"' && texto[i + 1] === '"') { campo += '"'; i++; }
        else if (c === '"') aspas = false;
        else campo += c;
      } else if (c === '"') aspas = true;
      else if (c === ",") { linha.push(campo); campo = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && texto[i + 1] === "\n") i++;
        linha.push(campo); linhas.push(linha); linha = []; campo = "";
      } else campo += c;
    }
    if (campo || linha.length) { linha.push(campo); linhas.push(linha); }
    var cab = linhas.shift() || [];
    return linhas.filter(function (l) { return l.join("").trim(); }).map(function (l) {
      var o = {}; cab.forEach(function (k, j) { o[k.trim()] = (l[j] || "").trim(); }); return o;
    });
  }

  function manualParaOferta(m) {
    var preco = parseFloat((m.preco || "").replace(",", "."));
    var antigo = parseFloat((m.preco_antigo || "").replace(",", "."));
    if (!m.nome || !m.link || !preco) return null;
    return {
      chave: "manual-" + m.link, nome: m.nome, preco: preco,
      preco_antigo: antigo || null,
      desconto: antigo > preco ? Math.round((1 - preco / antigo) * 100) : 0,
      categoria: m.categoria || "Presentes", plataforma: m.loja || "Loja",
      loja: "", foto: m.foto || "", link: m.link, data: m.data || ""
    };
  }

  function carregar(url, tipo) {
    return fetch(url, { cache: "no-store" }).then(function (r) {
      if (!r.ok) return tipo === "json" ? [] : "";
      return tipo === "json" ? r.json() : r.text();
    }).catch(function () { return tipo === "json" ? [] : ""; });
  }

  Promise.all([carregar("ofertas.json", "json"), carregar("manuais.csv", "texto")]).then(function (res) {
    var manuais = lerCSV(res[1] || "").map(manualParaOferta).filter(Boolean);
    estado.ofertas = (res[0] || []).concat(manuais);
    if (pagina === "black-friday") estado.ofertas.sort(function (a, b) { return (b.desconto || 0) - (a.desconto || 0); });
    else estado.ofertas.sort(function (a, b) { return (b.data || "").localeCompare(a.data || ""); });
    montarChips();
    desenhar();
  });

  function montarChips() {
    if (!chips) return;
    CATEGORIAS.forEach(function (cat) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = cat;
      b.setAttribute("aria-pressed", cat === estado.categoria ? "true" : "false");
      b.addEventListener("click", function () {
        estado.categoria = cat;
        chips.querySelectorAll(".chip").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        desenhar();
      });
      chips.appendChild(b);
    });
  }

  if (busca) busca.addEventListener("input", function () { estado.busca = semAcento(busca.value); desenhar(); });

  // Cupons e promoções das marcas (docs/cupons.json). Some sozinho depois da data de validade.
  var caixaCupons = document.getElementById("lista-cupons");
  if (caixaCupons) {
    carregar("cupons.json", "json").then(function (lista) {
      var hoje = new Date().toISOString().slice(0, 10);
      var validos = (lista || []).filter(function (c) { return !c.ate || c.ate >= hoje; });
      if (pagina === "black-friday") validos.sort(function (a, b) { return (a.ate || "").localeCompare(b.ate || ""); });
      validos = intercalar(validos.map(function (c) { c.plataforma = c.marca; return c; }));
      if (!validos.length) { document.getElementById("cupons").hidden = true; return; }
      validos.forEach(function (c) { caixaCupons.appendChild(cartaoCupom(c)); });
    });
  }

  function cartaoCupom(c) {
    var li = document.createElement("li"); li.className = "cupom";
    var topo = document.createElement("div"); topo.className = "cupom-topo";
    var marca = document.createElement("span"); marca.className = "cupom-marca"; marca.textContent = c.marca;
    var ate = document.createElement("span"); ate.className = "cupom-ate"; ate.textContent = c.ate ? "até " + dataCurta(c.ate) : "";
    topo.appendChild(marca); topo.appendChild(ate); li.appendChild(topo);
    var t = document.createElement("p"); t.className = "cupom-titulo"; t.textContent = c.titulo; li.appendChild(t);
    var a = document.createElement("a");
    a.className = "botao violeta"; a.href = c.link; a.target = "_blank"; a.rel = "noopener sponsored";
    if (c.cupom) {
      var cod = document.createElement("div"); cod.className = "cupom-codigo"; cod.textContent = c.cupom; li.appendChild(cod);
      a.textContent = "Copiar cupom e ir à loja";
      a.addEventListener("click", function () {
        try { navigator.clipboard.writeText(c.cupom); } catch (e) {}
        cod.textContent = c.cupom + " ✓ copiado";
      });
    } else {
      a.textContent = "Ver promoção";
    }
    li.appendChild(a);
    return li;
  }

  function cartao(o) {
    var li = document.createElement("li"); li.className = "cartao";
    var foto = document.createElement("div"); foto.className = "foto";
    if (o.foto) {
      var img = document.createElement("img");
      img.src = o.foto; img.alt = o.nome; img.loading = "lazy";
      img.onerror = function () { foto.removeChild(img); semFoto(foto); };
      foto.appendChild(img);
    } else semFoto(foto);
    if (o.desconto >= 5) {
      var selo = document.createElement("span"); selo.className = "selo"; selo.textContent = "-" + Math.round(o.desconto) + "%";
      foto.appendChild(selo);
    }
    var tag = document.createElement("span"); tag.className = "loja-tag"; tag.textContent = o.plataforma || "Shopee";
    foto.appendChild(tag);
    li.appendChild(foto);

    var info = document.createElement("div"); info.className = "info";
    var h3 = document.createElement("h3"); h3.textContent = o.nome; info.appendChild(h3);
    var precos = document.createElement("div"); precos.className = "precos";
    if (o.preco_antigo) { var ant = document.createElement("span"); ant.className = "antigo"; ant.textContent = moeda(o.preco_antigo); ant.setAttribute("aria-label", "Antes " + moeda(o.preco_antigo)); precos.appendChild(ant); }
    var atual = document.createElement("span"); atual.className = "atual"; atual.textContent = moeda(o.preco); precos.appendChild(atual);
    info.appendChild(precos);
    var det = document.createElement("p"); det.className = "detalhes";
    var partes = [];
    if (o.nota) partes.push("★ " + String(o.nota).replace(".", ","));
    if (o.vendas) partes.push(Number(o.vendas).toLocaleString("pt-BR") + " vendidos");
    if (o.data) partes.push("achado em " + dataCurta(o.data));
    det.textContent = partes.join(" · ");
    info.appendChild(det);
    var a = document.createElement("a");
    a.className = "botao violeta"; a.href = o.link; a.target = "_blank"; a.rel = "noopener sponsored";
    var loja = o.plataforma || "Shopee";
    a.textContent = "Comprar";
    a.setAttribute("aria-label", "Comprar " + o.nome + " em " + loja);
    info.appendChild(a);
    li.appendChild(info);
    return li;
  }

  function semFoto(el) {
    var s = document.createElement("span"); s.className = "sem-foto"; s.textContent = "papai achou"; el.insertBefore(s, el.firstChild);
  }

  // Rodízio entre as lojas/marcas: um produto de cada loja por vez (Magalu, Mercado Livre, Nike,
  // Shopee, Kabum...), para a vitrine ficar variada. Quando uma loja acaba, as outras continuam o rodízio.
  // Dentro de cada loja, vem primeiro o maior desconto entre os achados mais recentes.
  function intercalar(lista) {
    var grupos = {}, ordem = [];
    lista.forEach(function (o) {
      var k = o.plataforma || "Shopee";
      if (!grupos[k]) { grupos[k] = []; ordem.push(k); }
      grupos[k].push(o);
    });
    // Lojas com menos produtos entram primeiro na roda, para aparecerem logo no topo.
    ordem.sort(function (a, b) { return grupos[a].length - grupos[b].length; });
    ordem.forEach(function (k) {
      grupos[k].sort(function (a, b) {
        var porDesconto = (b.desconto || 0) - (a.desconto || 0);
        if (pagina === "black-friday") return porDesconto;  // na Black Friday, maior desconto primeiro
        return (b.data || "").slice(0, 10).localeCompare((a.data || "").slice(0, 10)) || porDesconto;
      });
    });
    var resultado = [], resta = true;
    while (resta) {
      resta = false;
      ordem.forEach(function (k) {
        if (grupos[k].length) { resultado.push(grupos[k].shift()); resta = true; }
      });
    }
    return resultado;
  }

  function desenhar() {
    var lista = intercalar(estado.ofertas.filter(function (o) {
      var okCat = estado.categoria === "Todos" || o.categoria === estado.categoria;
      var okBusca = !estado.busca || semAcento(o.nome + " " + o.categoria).indexOf(estado.busca) >= 0;
      return okCat && okBusca;
    }));
    grade.innerHTML = "";
    if (!estado.ofertas.length) {
      grade.innerHTML = '<li class="vazio"><h2>Os primeiros achados estão chegando</h2><p>Enquanto isso, entre no canal para receber as ofertas assim que o papai achar.</p></li>';
      contagem.textContent = "";
      return;
    }
    contagem.textContent = lista.length === 1 ? "1 achado" : lista.length + " achados";
    if (!lista.length) {
      grade.innerHTML = '<li class="vazio"><h2>Nada por aqui ainda</h2><p>Tente outra palavra ou outra categoria.</p></li>';
      return;
    }
    lista.forEach(function (o) { grade.appendChild(cartao(o)); });
  }

  function iniciarContagem() {
    var alvo = new Date(cfg.blackFriday || "2026-11-27T00:00:00-03:00").getTime();
    var caixa = document.getElementById("regressiva");
    if (!caixa) return;
    function tick() {
      var falta = alvo - Date.now();
      if (falta <= 0) { caixa.innerHTML = "<div><b>É hoje!</b>Black Friday</div>"; return; }
      var d = Math.floor(falta / 864e5), h = Math.floor(falta / 36e5) % 24, m = Math.floor(falta / 6e4) % 60;
      caixa.innerHTML = "<div><b>" + d + "</b>dias</div><div><b>" + h + "</b>horas</div><div><b>" + m + "</b>min</div>";
    }
    tick(); setInterval(tick, 30000);
  }
})();
