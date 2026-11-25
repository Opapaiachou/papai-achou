(function () {
  var CATEGORIAS = ["Todos", "Fitness", "Casa e cozinha", "Escola", "Crianças", "Moda", "Maquiagem e beleza", "Tecnologia útil", "Gamer", "Presentes"];
  var pagina = document.body.getAttribute("data-pagina");
  var cfg = window.PAPAI_ACHOU || {};
  var estado = { ofertas: [], categoria: "Todos", busca: "", ordem: "melhores" };

  // ---------- Medição (Google Analytics 4) ----------
  // Liga sozinho quando o config.js tiver o código ga4 ("G-..."). Sem código, nada é enviado.
  // As campanhas são lidas dos parâmetros utm_ do link (ex.: ?utm_source=instagram&utm_medium=bio).
  if (/^G-[A-Z0-9]+$/.test(cfg.ga4 || "")) {
    var tag = document.createElement("script");
    tag.async = true; tag.src = "https://www.googletagmanager.com/gtag/js?id=" + cfg.ga4;
    document.head.appendChild(tag);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", cfg.ga4);
  }
  function medir(evento, dados) {
    try { if (window.gtag) window.gtag("event", evento, dados || {}); } catch (e) {}
  }

  // Links das redes (vêm do config.js)
  document.querySelectorAll("[data-link]").forEach(function (a) {
    var url = cfg[a.getAttribute("data-link")];
    if (url && url !== "#") { a.href = url; a.target = "_blank"; a.rel = "noopener"; }
    a.addEventListener("click", function () { medir("clique_rede", { rede: a.getAttribute("data-link"), pagina: pagina }); });
  });
  // Faixa da Black Friday some sozinha depois da data.
  document.querySelectorAll("[data-ate]").forEach(function (el) {
    if (new Date().toISOString().slice(0, 10) > el.getAttribute("data-ate")) el.remove();
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

  // Cupons das marcas (docs/cupons.json): o código aparece na descrição do produto a que se refere.
  // Some sozinho depois da data de validade. Ao tocar em Comprar, o cupom também é copiado.
  var GENERICAS = /^(off|produtos?|selecionad[oa]s?|campanha|participantes|marca|maga|na|no|nos|nas|em|da|de|do|dos|das|com|e|a|o|r|para|lista|leve|pague)$/;
  var cupons = [];
  function palavras(t) { return semAcento(t).replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter(function (w) { return w.length > 1 && !/^\d+$/.test(w) && !GENERICAS.test(w); }); }
  function cupomDo(o) {
    var nome = " " + palavras(o.nome).join(" ") + " ";
    for (var i = 0; i < cupons.length; i++) {
      var c = cupons[i];
      if (c.marca !== o.plataforma) continue;
      var achou = c.palavras.filter(function (w) { return nome.indexOf(" " + w + " ") >= 0; }).length;
      // Se o cupom cita um modelo (ex.: L4360, DDR4), o produto precisa ter esse modelo no nome.
      var modelos = c.palavras.filter(function (w) { return /\d/.test(w) && /[a-z]/.test(w) && !/^\d+(v|gb|tb|mhz|hz|cm|mm|ml|w)$/.test(w); });
      var temModelo = !modelos.length || modelos.some(function (w) { return nome.indexOf(" " + w + " ") >= 0; });
      if (achou && temModelo && achou >= Math.min(3, c.palavras.length)) return c;
    }
    return null;
  }
  var pedidoCupons = carregar("cupons.json", "json").then(function (lista) {
    var hoje = new Date().toISOString().slice(0, 10);
    cupons = (lista || []).filter(function (c) { return c.cupom && (!c.ate || c.ate >= hoje); })
      .map(function (c) { c.palavras = palavras(c.titulo.replace(/^.*?\b(OFF|off)\b/, "")); return c; })
      .filter(function (c) { return c.palavras.length; });
  });

  Promise.all([carregar("ofertas.json", "json"), carregar("manuais.csv", "texto"), pedidoCupons]).then(function (res) {
    var manuais = lerCSV(res[1] || "").map(manualParaOferta).filter(Boolean);
    estado.ofertas = (res[0] || []).concat(manuais);
    // Produtos gamer (Kabum e outras lojas) ficam na categoria Gamer, mesmo os que já estavam no site.
    var gamer = /\b(gamer|gaming|headset|xbox|playstation|ps4|ps5|nintendo|dualsense|joystick|console|controle sem fio|placa de v[ií]deo|rtx|radeon|geforce|ddr4|ddr5|mem[oó]ria ram|ssd|nvme|water ?cooler|mousepad|teclado mec[aâ]nico|cadeira gamer|hyperx|redragon|razer)\b/i;
    estado.ofertas.forEach(function (o) { if (gamer.test(o.nome || "")) o.categoria = "Gamer"; });
    // Marcas da Awin com desconto acima de 70% costumam ter "preço de" inflado: não aparecem.
    estado.ofertas = estado.ofertas.filter(function (o) { return !(/awin1\.com/.test(o.link || "") && (o.desconto || 0) > 70); });
    // Achado aberto por um link compartilhado (?achado=...): vai para o topo, em destaque.
    estado.maisRecente = estado.ofertas.reduce(function (m, o) { var t = new Date(o.data || 0).getTime(); return t > m ? t : m; }, 0);
    var pedido = new URLSearchParams(location.search).get("achado");
    if (pedido) {
      estado.destaque = estado.ofertas.filter(function (o) { return idDo(o) === pedido; })[0] || null;
      estado.destaquePerdido = !estado.destaque;
      medir("abriu_compartilhado", { encontrado: !!estado.destaque });
    }
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
        medir("filtro_categoria", { categoria: cat, pagina: pagina });
        desenhar();
      });
      chips.appendChild(b);
    });
  }

  var seletor = document.getElementById("ordem");
  if (pagina === "black-friday") estado.ordem = "desconto";
  if (seletor) {
    seletor.value = estado.ordem;
    seletor.addEventListener("change", function () { estado.ordem = seletor.value; medir("ordenar", { ordem: seletor.value }); desenhar(); });
  }
  if (busca) busca.addEventListener("input", function () {
    estado.busca = semAcento(busca.value); desenhar();
    clearTimeout(busca.tempo);
    busca.tempo = setTimeout(function () { if (busca.value.trim().length > 2) medir("search", { search_term: busca.value.trim().slice(0, 60) }); }, 1500);
  });

  // Identificador curto e estável de cada achado, usado no link de compartilhar.
  function idDo(o) {
    var t = o.chave || o.link || o.nome || "", h = 5381;
    for (var i = 0; i < t.length; i++) h = ((h * 33) ^ t.charCodeAt(i)) >>> 0;
    return h.toString(36);
  }
  function linkDoAchado(o) {
    return location.origin + location.pathname + "?achado=" + idDo(o) + "&utm_source=compartilhar&utm_medium=social";
  }
  function avisar(texto) {
    var t = document.getElementById("aviso");
    if (!t) { t = document.createElement("div"); t.id = "aviso"; t.className = "aviso"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = texto; t.classList.add("ver");
    clearTimeout(avisar.tempo); avisar.tempo = setTimeout(function () { t.classList.remove("ver"); }, 2500);
  }
  function copiar(texto) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
    var c = document.createElement("textarea"); c.value = texto; c.setAttribute("readonly", ""); c.style.position = "fixed"; c.style.opacity = "0";
    document.body.appendChild(c); c.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(c);
    return Promise.resolve();
  }
  function compartilhar(o, botao) {
    var url = linkDoAchado(o);
    var texto = "Olha esse achado do Papai Achou: " + o.nome + " por " + moeda(o.preco) + (o.desconto >= 5 ? " (-" + Math.round(o.desconto) + "%)" : "");
    var dados = { produto: o.nome.slice(0, 90), loja: o.plataforma || "", categoria: o.categoria || "" };
    if (navigator.share) {
      navigator.share({ title: "Papai Achou", text: texto, url: url }).then(function () {
        dados.metodo = "nativo"; medir("compartilhar", dados);
      }).catch(function () {});
      return;
    }
    // Computador: menu simples com WhatsApp e copiar link.
    var aberto = document.querySelector(".menu-compartilhar");
    if (aberto) { var era = aberto.parentNode === botao.parentNode; aberto.remove(); if (era) return; }
    var menu = document.createElement("div"); menu.className = "menu-compartilhar";
    var zap = document.createElement("a");
    zap.href = "https://wa.me/?text=" + encodeURIComponent(texto + "\n" + url); zap.target = "_blank"; zap.rel = "noopener";
    zap.textContent = "Enviar no WhatsApp";
    zap.addEventListener("click", function () { dados.metodo = "whatsapp"; medir("compartilhar", dados); menu.remove(); });
    var cop = document.createElement("button"); cop.type = "button"; cop.textContent = "Copiar link";
    cop.addEventListener("click", function () {
      copiar(url).then(function () { avisar("Link copiado ✓"); });
      dados.metodo = "copiar"; medir("compartilhar", dados); menu.remove();
    });
    menu.appendChild(zap); menu.appendChild(cop);
    botao.parentNode.appendChild(menu);
  }
  document.addEventListener("click", function (e) {
    var m = document.querySelector(".menu-compartilhar");
    if (m && !m.contains(e.target) && !e.target.closest(".compartilhar")) m.remove();
  });
  document.addEventListener("keydown", function (e) {
    var m = document.querySelector(".menu-compartilhar"); if (e.key === "Escape" && m) m.remove();
  });

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
    if (o.preco_antigo && o.preco_antigo - o.preco >= 1) {
      var eco = document.createElement("p"); eco.className = "economia";
      eco.textContent = "Economize " + moeda(o.preco_antigo - o.preco) + (o.forma_preco ? " " + o.forma_preco : "");
      info.appendChild(eco);
    }
    var det = document.createElement("p"); det.className = "detalhes";
    var partes = [];
    var horas = o.data ? (Date.now() - new Date(o.data).getTime()) / 36e5 : 99;
    // "Novo" só para o que entrou na última rodada do robô (até 3h antes da mais recente).
    if (o.data && estado.maisRecente && estado.maisRecente - new Date(o.data).getTime() < 3 * 36e5) { var novo = document.createElement("span"); novo.className = "novo"; novo.textContent = "Novo"; foto.appendChild(novo); }
    if (o.nota) partes.push("★ " + String(o.nota).replace(".", ",") + (o.avaliacoes ? " (" + Number(o.avaliacoes).toLocaleString("pt-BR") + ")" : ""));
    if (o.vendas) partes.push(Number(o.vendas).toLocaleString("pt-BR") + " vendidos");
    if (o.data && horas >= 24) partes.push("achado em " + dataCurta(o.data));
    det.textContent = partes.join(" · ");
    info.appendChild(det);
    var cp = cupomDo(o);
    if (cp) {
      var cod = document.createElement("p"); cod.className = "cupom-produto";
      cod.style.cssText = "margin:.25rem 0 .5rem;font-size:.85rem;font-weight:700;color:#5B2EFF";
      cod.textContent = "🎟️ Use o cupom " + cp.cupom + (cp.ate ? " (até " + dataCurta(cp.ate) + ")" : "");
      info.appendChild(cod);
    }
    var a = document.createElement("a");
    a.className = "botao violeta"; a.href = o.link; a.target = "_blank"; a.rel = "noopener sponsored";
    var loja = o.plataforma || "Shopee";
    a.textContent = "Comprar";
    a.setAttribute("aria-label", "Comprar " + o.nome + " em " + loja);
    a.addEventListener("click", function () {
      medir("clique_comprar", { loja: loja, categoria: o.categoria || "", produto: o.nome.slice(0, 90),
        value: Number(o.preco) || 0, currency: "BRL", desconto: Math.round(o.desconto || 0), pagina: pagina });
      if (cp) { copiar(cp.cupom); cod.textContent = "🎟️ Cupom " + cp.cupom + " copiado ✓"; }
    });
    var acoes = document.createElement("div"); acoes.className = "acoes";
    var sh = document.createElement("button"); sh.type = "button"; sh.className = "compartilhar";
    sh.setAttribute("aria-label", "Compartilhar " + o.nome);
    sh.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M18 16.1c-.8 0-1.5.3-2 .8l-7.1-4.1c.1-.3.1-.5.1-.8s0-.5-.1-.8l7-4.1c.5.5 1.3.8 2.1.8 1.7 0 3-1.3 3-3s-1.3-3-3-3-3 1.3-3 3c0 .3 0 .5.1.8l-7 4.1C8.5 9.3 7.8 9 7 9c-1.7 0-3 1.3-3 3s1.3 3 3 3c.8 0 1.5-.3 2-.8l7.1 4.2c-.1.2-.1.4-.1.7 0 1.6 1.3 2.9 2.9 2.9s2.9-1.3 2.9-2.9-1.2-3-2.8-3z"/></svg>';
    sh.addEventListener("click", function () { compartilhar(o, sh); });
    acoes.appendChild(a); acoes.appendChild(sh);
    info.appendChild(acoes);
    li.appendChild(info);
    return li;
  }

  function semFoto(el) {
    var s = document.createElement("span"); s.className = "sem-foto"; s.textContent = "papai achou"; el.insertBefore(s, el.firstChild);
  }

  // Ordem da vitrine. "Melhores achados" pontua desconto (até 60%), nota, avaliações/vendas e quão recente é.
  // Depois mistura lojas e categorias (veja intercalar).
  function pontos(o) {
    var p = Math.min(o.desconto || 0, 60);
    if (o.nota) p += (o.nota - 4) * 20;
    var prova = (o.avaliacoes || 0) + (o.vendas || 0);
    if (prova) p += Math.min(Math.log10(prova) * 5, 15);
    var dias = o.data ? (Date.now() - new Date(o.data).getTime()) / 864e5 : 3;
    return p - Math.max(dias, 0) * 4;
  }
  var COMPARAR = {
    melhores: function (a, b) { return pontos(b) - pontos(a); },
    desconto: function (a, b) { return (b.desconto || 0) - (a.desconto || 0); },
    menor: function (a, b) { return a.preco - b.preco; },
    recentes: function (a, b) { return (b.data || "").localeCompare(a.data || ""); }
  };
  function intercalar(lista) {
    var fila = lista.slice().sort(COMPARAR[estado.ordem] || COMPARAR.melhores);
    if (estado.ordem === "menor") return fila;  // por preço, a ordem é a ordem
    // Variedade: escolhe o mais bem colocado da fila, com duas regras:
    // - no máximo 2 achados seguidos da mesma loja, se houver outra loja disponível (lojas intercaladas);
    // - repetir uma categoria dos últimos 4 cards custa 60 posições (categorias misturadas).
    var resultado = [];
    function k(o) { return o.plataforma || "Shopee"; }
    while (fila.length) {
      var n = resultado.length, rc = resultado.slice(-4);
      var travada = n >= 2 && k(resultado[n - 1]) === k(resultado[n - 2]) ? k(resultado[n - 1]) : null;
      if (travada && !fila.some(function (o) { return k(o) !== travada; })) travada = null;
      var melhor = -1, nota = -1e9;
      for (var j = 0; j < fila.length; j++) {
        var c = fila[j];
        if (travada && k(c) === travada) continue;
        var v = -j;
        rc.forEach(function (r) { if (r.categoria === c.categoria) v -= 60; });
        if (v > nota) { nota = v; melhor = j; }
      }
      resultado.push(fila.splice(melhor, 1)[0]);
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
    var ultima = estado.ofertas.reduce(function (m, o) { return (o.data || "") > m ? o.data : m; }, "");
    var hora = ultima ? new Date(ultima) : null;
    contagem.textContent = (lista.length === 1 ? "1 achado" : lista.length + " achados") +
      (hora && !isNaN(hora) ? " · atualizado " + (hora.toDateString() === new Date().toDateString() ? "hoje às " : "em " + dataCurta(ultima) + " às ") +
        hora.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "");
    if (!lista.length) {
      grade.innerHTML = '<li class="vazio"><h2>Nada por aqui ainda</h2><p>Tente outra palavra ou outra categoria.</p></li>';
      return;
    }
    if (estado.destaquePerdido) {
      var sumiu = document.createElement("li"); sumiu.className = "vazio destaque-aviso";
      sumiu.innerHTML = "<h2>Esse achado já saiu</h2><p>O preço mudou ou acabou o estoque. Olha os achados de hoje aqui embaixo 👇</p>";
      grade.appendChild(sumiu);
    }
    var d = estado.destaque;
    if (d && lista.indexOf(d) >= 0) { lista.splice(lista.indexOf(d), 1); lista.unshift(d); }
    lista.forEach(function (o) {
      var c = cartao(o);
      if (o === d) c.classList.add("destaque");
      grade.appendChild(c);
    });
    if (d && !desenhar.rolou) { desenhar.rolou = true; var alvo = grade.querySelector(".destaque"); if (alvo) alvo.scrollIntoView({ block: "center" }); }
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
