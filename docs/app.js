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
    a.textContent = (loja === "Mercado Livre" ? "Ver no " : "Ver na ") + loja;
    info.appendChild(a);
    li.appendChild(info);
    return li;
  }

  function semFoto(el) {
    var s = document.createElement("span"); s.className = "sem-foto"; s.textContent = "papai achou"; el.insertBefore(s, el.firstChild);
  }

  function desenhar() {
    var lista = estado.ofertas.filter(function (o) {
      var okCat = estado.categoria === "Todos" || o.categoria === estado.categoria;
      var okBusca = !estado.busca || semAcento(o.nome + " " + o.categoria).indexOf(estado.busca) >= 0;
      return okCat && okBusca;
    });
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
