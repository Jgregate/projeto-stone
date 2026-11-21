// Jade. Interface do contrato do agente (Entrada e Saida de agente.py).
// Regra de ouro: números exibidos vêm dos campos da base (findings, reference_posts e
// detalhes). Texto do modelo é mostrado como texto, em fonte serifada, com a origem indicada.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// ------------------------------------------------------------------ vocabulário
const CAMPOS = {
  tipo_post: "Tipo de publicação",
  formato_video: "Formato do vídeo",
  tipo_hook: "Gancho",
  tema_principal: "Tema",
  tom: "Tom",
  tem_rosto: "Rosto na capa",
  texto_na_tela: "Texto na tela",
  tem_cta: "Chamada para ação",
  tipo_cta: "Tipo de chamada",
  oferta_ou_beneficio_explicito: "Oferta ou benefício explícito",
  legenda_tamanho: "Tamanho da legenda",
};
const VALORES = {
  reels: "Reels", carrossel: "Carrossel", imagem: "Imagem", short: "Short", video: "Vídeo",
  instagram: "Instagram", youtube: "YouTube Shorts",
  micro: "Micro", medio: "Médio", grande: "Grande",
  financas: "Finanças", gestao: "Gestão", marketing: "Marketing", vendas: "Vendas", atendimento: "Atendimento",
  motivacao: "Motivação", ferramentas_maquininha: "Ferramentas e maquininha",
  historia_de_empreendedor: "História de empreendedor",
  alimentacao: "Alimentação", beleza: "Beleza", varejo: "Varejo",
  curiosidade: "Curiosidade", promessa: "Promessa", pergunta: "Pergunta", dor: "Dor", polemica: "Polêmica",
  numero: "Número", nenhum: "Nenhum",
  depoimento: "Depoimento", tutorial: "Tutorial", humor_esquete: "Humor ou esquete", talking_head: "Pessoa falando para a câmera",
  bastidores: "Bastidores", lista_dicas: "Lista de dicas", antes_depois: "Antes e depois",
  informal: "Informal", inspiracional: "Inspiracional", educativo: "Educativo", tecnico: "Técnico", humoristico: "Humorístico",
  link_na_bio: "Link na bio", comentar: "Comentar", salvar: "Salvar", seguir: "Seguir", compartilhar: "Compartilhar", dm: "Mensagem direta",
  curta: "Curta", media: "Média", longa: "Longa",
  True: "Sim", False: "Não", true: "Sim", false: "Não",
};
const MODOS = {
  analisar: { nome: "Analisar", botao: "Analisar publicações" },
  recomendar: { nome: "Recomendar", botao: "Gerar recomendações" },
  gerar_criativo: { nome: "Criar criativo", botao: "Criar criativo" },
};
const FILTROS = ["plataforma", "tipo_post", "faixa", "tema_principal"];
const NOME_FILTRO = { segmento: "segmento", plataforma: "plataforma", tipo_post: "tipo de publicação", faixa: "tamanho do perfil", tema_principal: "tema" };

const juntar = (l) => (l.length < 2 ? l.join("") : l.slice(0, -1).join(", ") + " e " + l.at(-1));
const rotulo = (v) => (v == null ? "Sem dado" : VALORES[String(v)] ?? String(v).replaceAll("_", " "));
const fmt = {
  int: (n) => (n == null ? "sem dado" : Math.round(n).toLocaleString("pt-BR")),
  pct: (x, casas = 0) => (x == null ? "sem dado" : (x * 100).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }) + "%"),
  lift: (x) => (x == null ? "sem dado" : x.toLocaleString("pt-BR", { maximumFractionDigits: x >= 100 ? 0 : 1 }) + "×"),
  data: (s) => (s ? s.split("-").reverse().join("/") : ""),
};

function el(tag, attrs = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f != null && f !== false) n.append(f instanceof Node ? f : document.createTextNode(f));
  return n;
}
const anunciar = (t) => { const a = $("#anuncio"); a.textContent = ""; setTimeout(() => (a.textContent = t), 60); };

const ICONE_AVISO = () => {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("aria-hidden", "true");
  s.innerHTML = '<path d="M12 3 2 21h20L12 3Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="18" r="1.2" fill="currentColor"/>';
  return s;
};

// ------------------------------------------------------------------ abas
function iniciarAbas() {
  const abas = $$('[role="tab"]');
  const selecionar = (aba, focar = true) => {
    for (const a of abas) {
      const sel = a === aba;
      a.setAttribute("aria-selected", sel);
      a.tabIndex = sel ? 0 : -1;
      $("#" + a.getAttribute("aria-controls")).hidden = !sel;
    }
    if (focar) aba.focus();
    if (aba.id === "aba-base") carregarBase();
  };
  abas.forEach((a, i) => {
    a.addEventListener("click", () => selecionar(a));
    a.addEventListener("keydown", (e) => {
      const mapa = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: abas.length - 1 };
      if (!(e.key in mapa)) return;
      e.preventDefault();
      selecionar(abas[(mapa[e.key] + abas.length) % abas.length]);
    });
  });
}

// ------------------------------------------------------------------ formulário
const form = $("#form");
const botao = $("#enviar");

function modoAtual() { return form.elements.mode.value; }
function atualizarModo() {
  const m = modoAtual();
  botao.textContent = MODOS[m].botao;
  $("#campo-n").hidden = m !== "gerar_criativo";
}
function atualizarResumoFiltros() {
  const ativos = FILTROS.filter((f) => form.elements[f].value).map((f) => rotulo(form.elements[f].value));
  $("#filtros-resumo").textContent = ativos.length ? `(${ativos.join(", ")})` : "";
}
function lerEntrada() {
  const f = form.elements;
  const filters = {};
  for (const k of FILTROS) filters[k] = f[k].value || null;
  const e = { mode: modoAtual(), query: f.query.value.trim(), segment: f.segment.value || null, filters };
  if (e.mode === "gerar_criativo") e.n_criativos = Number(f.n_criativos.value);
  return e;
}
function preencher(ex) {
  const f = form.elements;
  f.mode.value = ex.mode;
  f.query.value = ex.query;
  f.segment.value = ex.segment || "";
  for (const k of FILTROS) f[k].value = ex.filters?.[k] || "";
  f.n_criativos.value = String(ex.n_criativos || 1);
  $("#filtros").open = FILTROS.some((k) => ex.filters?.[k]);
  atualizarModo(); atualizarResumoFiltros();
}

async function carregarExemplos() {
  try {
    const lista = await (await fetch("/api/exemplos")).json();
    for (const ul of [$("#exemplos"), $("#exemplos-iniciais")]) {
      for (const ex of lista) {
        ul.append(el("li", {}, el("button", {
          type: "button", class: "exemplo",
          onclick: () => { preencher(ex); consultar(); },
        }, el("span", { class: "exemplo__modo", text: MODOS[ex.mode].nome }), el("span", { class: "exemplo__titulo", text: ex.titulo }),
          ul.id === "exemplos-iniciais" ? el("span", { class: "exemplo__pedido", text: ex.query }) : null)));
      }
    }
  } catch { /* sem exemplos, o formulário continua funcionando */ }
}

let ocupado = false;
let cronometro;
async function consultar() {
  if (ocupado) return;
  const entrada = lerEntrada();
  const q = form.elements.query;
  if (!entrada.query) {
    q.setAttribute("aria-invalid", "true"); $("#query-erro").hidden = false; q.focus(); return;
  }
  q.removeAttribute("aria-invalid"); $("#query-erro").hidden = true;

  ocupado = true;
  botao.setAttribute("aria-disabled", "true");
  const textoBotao = botao.textContent;
  botao.textContent = "Consultando";
  $("#carregando").hidden = false;
  $("#saida").setAttribute("aria-busy", "true");
  const t0 = performance.now();
  const tempo = $("#tempo");
  tempo.hidden = false;
  tempo.textContent = entrada.mode === "gerar_criativo" ? "Escrever o criativo leva de 10 a 40 segundos." : "A consulta leva de 5 a 30 segundos.";
  cronometro = setInterval(() => {
    const s = Math.round((performance.now() - t0) / 1000);
    if (s > 45) tempo.textContent = `Ainda consultando, ${s} segundos. O modelo pode estar mais lento agora.`;
  }, 1000);

  let resp, corpo;
  try {
    resp = await fetch("/api/consultar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(entrada) });
    corpo = await resp.json().catch(() => ({}));
  } catch {
    resp = null;
  } finally {
    clearInterval(cronometro);
    ocupado = false;
    botao.removeAttribute("aria-disabled");
    botao.textContent = textoBotao;
    $("#carregando").hidden = true;
    tempo.hidden = true;
    $("#saida").removeAttribute("aria-busy");
  }
  $("#estado-inicial").hidden = true;
  const saida = $("#saida");
  saida.replaceChildren();

  if (!resp) {
    saida.append(aviso("erro", "O servidor local não respondeu",
      ["Confira se o terminal com o frontend continua aberto e tente de novo."], tentarDeNovo()));
  } else if (resp.status === 429) {
    saida.append(aviso("erro", "O modelo de linguagem atingiu o limite de requisições",
      [`O Groq recusou novas chamadas por enquanto. Tente de novo em ${corpo.retry_after ?? 30} segundos.`,
        corpo.saida ? "Os dados da base abaixo continuam válidos. Só o texto do modelo ficou de fora." : ""], tentarDeNovo(corpo.retry_after)));
    if (corpo.saida) renderizar(corpo, saida);
  } else if (resp.status === 404) {
    saida.append(semResultado(corpo, entrada));
  } else if (resp.status === 400 || resp.status === 422) {
    saida.append(aviso("erro", "O pedido não foi aceito", [corpo.mensagem || "Confira o modo, o pedido e os filtros e tente de novo."]));
  } else if (!resp.ok) {
    saida.append(aviso("erro", "A consulta falhou no servidor", ["Veja o terminal do frontend para o detalhe do erro e tente de novo."], tentarDeNovo()));
  } else {
    renderizar(corpo, saida);
  }
  $("#resultado").focus({ preventScroll: true });
  $("#resultado").scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  anunciar(resp && resp.ok ? "Resultado pronto." : "A consulta terminou com um aviso.");
}

function tentarDeNovo(segundos) {
  const b = el("button", { type: "button", class: "botao botao--secundario", onclick: consultar, text: "Consultar de novo" });
  if (segundos && segundos < 120) {
    b.setAttribute("aria-disabled", "true");
    let r = Math.round(segundos);
    b.textContent = `Consultar de novo em ${r} s`;
    const t = setInterval(() => {
      r -= 1;
      if (r <= 0) { clearInterval(t); b.removeAttribute("aria-disabled"); b.textContent = "Consultar de novo"; }
      else b.textContent = `Consultar de novo em ${r} s`;
    }, 1000);
    b.addEventListener("click", (e) => { if (b.getAttribute("aria-disabled")) e.stopImmediatePropagation(); }, { capture: true });
  }
  return b;
}

function aviso(tipo, titulo, linhas = [], acao) {
  const papel = tipo === "erro" ? "alert" : null;
  return el("div", { class: "aviso" + (tipo === "erro" ? " aviso--erro" : ""), role: papel },
    ICONE_AVISO(),
    el("div", {}, el("h3", { text: titulo }), ...linhas.filter(Boolean).map((l) => (l instanceof Node ? l : el("p", { text: l }))), acao || null));
}

function semResultado(corpo, entrada) {
  const linhas = [];
  if (corpo.termos?.length) linhas.push(`Nenhuma publicação de alto desempenho da base menciona ${corpo.termos.map((t) => `“${t}”`).join(", ")}.`);
  else linhas.push(corpo.mensagem || "Nenhuma publicação de alto desempenho atende a esse pedido.");
  linhas.push("Reescreva o pedido com palavras do dia a dia do empreendedor, como vendas, caixa, salão ou delivery, ou retire filtros.");
  return el("div", { class: "vazio" }, el("h2", { text: "Nenhuma publicação encontrada" }), ...linhas.map((l) => el("p", { text: l })));
}

// ------------------------------------------------------------------ renderização do resultado
function renderizar(corpo, alvo) {
  const s = corpo.saida;
  const det = corpo.detalhes || {};
  const numero = new Map(s.reference_posts.map((p, i) => [p.post_id, i + 1]));
  const ctx = { s, det, numero, citados: corpo.citados || {} };

  alvo.append(cabecalho(s, corpo));
  const conf = avisoConfianca(s, corpo);
  if (conf) alvo.append(conf);
  if (corpo.falha_modelo) {
    alvo.append(aviso("erro", "O texto do modelo não foi gerado", [`Motivo ${corpo.falha_modelo}.`, "Os achados e as publicações abaixo vêm da base e continuam válidos."]));
  }

  if (s.mode === "gerar_criativo") {
    if (s.creatives.length) alvo.append(blocoCriativos(s, ctx));
    else if (!corpo.erro) alvo.append(aviso("erro", "Nenhum criativo foi gerado", ["O modelo respondeu fora do formato esperado. Consulte de novo."], tentarDeNovo()));
  }
  alvo.append(blocoExplicacao(s, corpo, ctx));
  alvo.append(blocoReferencias(s, ctx));
  alvo.append(blocoAchados(s, corpo.exemplos_achados));
}

function cabecalho(s, corpo) {
  const ap = s.filtros_aplicados || {};
  const ativos = Object.entries(ap).filter(([, v]) => v);
  const recorte = ativos.length
    ? " Recorte por " + juntar(ativos.map(([k, v]) => `${NOME_FILTRO[k] || k} ${rotulo(v).toLowerCase()}`)) + "."
    : " Sem recorte, toda a base de alto desempenho.";
  const partes = [el("span", {}, el("strong", { class: "num", text: fmt.int(s.n_posts_analisados) }), " publicações de alto desempenho analisadas.", recorte)];
  return el("header", { class: "cabecalho-resultado" },
    el("p", { class: "ajuda", text: MODOS[s.mode].nome }),
    el("h2", { id: "titulo-pedido", text: s.query }),
    el("p", { class: "recorte" }, ...partes));
}

function filtrosRetirados(s, corpo) {
  const pedidos = corpo.filtros_pedidos || {};
  const ap = s.filtros_aplicados || {};
  return Object.entries(pedidos).filter(([k, v]) => v && !ap[k]).map(([k]) => NOME_FILTRO[k] || k);
}

function avisoConfianca(s, corpo) {
  if (!s.confidence_flag) return null;
  const motivos = [];
  if (s.n_posts_analisados < 15) motivos.push(`O recorte tem só ${s.n_posts_analisados} publicações.`);
  const ret = filtrosRetirados(s, corpo);
  if (ret.length) motivos.push(`O filtro de ${ret.join(" e ")} foi retirado porque sobravam menos de 15 publicações.`);
  const fracos = s.findings.filter((a) => a.confidence_flag && ["tipo_hook", "tema_principal", "formato_video"].includes(a.campo));
  if (fracos.length) motivos.push(`${fracos.length} ${fracos.length === 1 ? "categoria aparece" : "categorias aparecem"} em menos de 10 publicações. Estão marcadas com listras no gráfico.`);
  if (!motivos.length) motivos.push("Para chegar a um recorte mínimo, o agente retirou filtros que detectou no próprio pedido.");
  return el("div", { class: "aviso", role: "note", "aria-label": "Aviso de confiança" }, ICONE_AVISO(),
    el("div", {}, el("h3", { text: "Poucas publicações sustentam este resultado" }),
      el("ul", {}, ...motivos.map((m) => el("li", { text: m }))),
      el("p", { text: "Trate como indício e confira as publicações de referência antes de decidir." })));
}

// texto com citações de post_id viradas em links rastreáveis
function limparTokens(texto) {
  return texto.replace(/\b([A-Za-z]+(?:_[a-z]+)+)\b/g, (t) => {
    const k = t.toLowerCase();
    const v = VALORES[k] || CAMPOS[k];
    if (!v) return t;
    return t[0] === t[0].toUpperCase() ? v : v.toLowerCase();
  });
}

function textoComCitacoes(texto, ctx) {
  texto = texto.replace(/post_?ids?\s*[:=]?\s*(?=(ig|yt)_)/gi, "");
  texto = limparTokens(texto);
  const frag = document.createDocumentFragment();
  const re = /\b(ig_\d{6,}|yt_[A-Za-z0-9_-]{11})/g;
  let ult = 0, m;
  while ((m = re.exec(texto))) {
    frag.append(texto.slice(ult, m.index));
    frag.append(citacao(m[1], ctx));
    ult = m.index + m[0].length;
  }
  frag.append(texto.slice(ult));
  return frag;
}

function citacao(pid, ctx) {
  const n = ctx.numero.get(pid);
  if (n) {
    const perfil = ctx.det[pid]?.perfil || "";
    const a = el("a", { class: "cita", href: `#ref-${n}`, "data-ref": n, "aria-label": `Publicação de referência ${n}, @${perfil}`, text: String(n) });
    ligarCitacao(a, n);
    return a;
  }
  const c = ctx.citados[pid];
  if (c?.na_base) return el("a", { class: "cita cita--externa", href: c.url, target: "_blank", rel: "noopener", "aria-label": `Publicação de @${c.perfil}, abre em nova aba`, text: "@" + c.perfil });
  return el("span", { class: "cita cita--fora", text: "não está na base", "aria-label": `Identificador ${pid} citado pelo modelo e não encontrado na base` });
}

function ligarCitacao(a, n) {
  const alvo = () => document.getElementById(`ref-${n}`);
  const on = () => { alvo()?.classList.add("destacada"); a.classList.add("ativa"); };
  const off = () => { if (!a.matches(":focus")) { alvo()?.classList.remove("destacada"); a.classList.remove("ativa"); } };
  a.addEventListener("pointerenter", on);
  a.addEventListener("pointerleave", off);
  a.addEventListener("focus", on);
  a.addEventListener("blur", () => { a.classList.remove("ativa"); alvo()?.classList.remove("destacada"); });
  a.addEventListener("click", (e) => {
    e.preventDefault();
    const r = alvo();
    if (!r) return;
    $$(".ref.destacada").forEach((x) => x.classList.remove("destacada"));
    r.classList.add("destacada");
    r.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    $("a", r)?.focus({ preventScroll: true });
    setTimeout(() => r.classList.remove("destacada"), 2400);
  });
}

function blocoCriativos(s, ctx) {
  const sec = el("section", { class: "criativos", "aria-labelledby": "criativos-titulo" },
    el("h3", { id: "criativos-titulo", class: "sr", text: "Criativos" }));
  s.creatives.forEach((c, i) => {
    const fontes = el("div", { class: "criativo__fontes" },
      el("h5", { text: `Inspirado em ${c.inspirado_em.length} ${c.inspirado_em.length === 1 ? "publicação" : "publicações"}` }),
      ...c.inspirado_em.map((pid) => fonteCriativo(pid, ctx)));
    const texto = el("div", { class: "criativo__texto" },
      el("div", { class: "criativo__topo" },
        el("h4", { text: s.creatives.length > 1 ? `Criativo ${i + 1}. ${c.titulo}` : c.titulo }),
        el("span", { text: limparTokens(c.formato) })),
      el("div", {}, el("p", { class: "rotulo", text: "Gancho" }), el("p", { class: "gancho", text: limparTokens(c.gancho) })),
      el("div", {}, el("p", { class: "rotulo", text: "Roteiro" }),
        el("ol", { class: "roteiro" }, ...c.roteiro.map((cena) => el("li", {}, el("span", { class: "roteiro__tempo", text: cena.tempo }), el("span", { text: limparTokens(cena.acao) }))))),
      el("div", {}, el("p", { class: "rotulo", text: "Legenda" }), el("p", { class: "legenda", text: limparTokens(c.legenda) })),
      el("div", {}, el("p", { class: "rotulo", text: "Chamada para ação" }), el("p", { class: "cta", text: c.cta })),
      el("div", {}, el("p", { class: "rotulo", text: "Por que este caminho" }), el("p", { class: "justificativa" }, textoComCitacoes(c.justificativa, ctx))),
      el("p", { class: "origem", text: "Texto redigido pelo modelo a partir dos achados e das publicações ao lado" }));
    sec.append(el("article", { class: "criativo", "aria-label": `Criativo ${i + 1}` }, texto, fontes));
  });
  return sec;
}

function fonteCriativo(pid, ctx) {
  const n = ctx.numero.get(pid);
  const d = ctx.det[pid];
  if (!d) return el("div", { class: "fonte" }, el("span", { class: "sem-imagem" }), el("div", {}, citacao(pid, ctx)));
  const img = d.imagem ? el("img", { src: d.imagem, alt: "", loading: "lazy", width: 44, height: 56 }) : el("span", { class: "sem-imagem" });
  const cita = citacao(pid, ctx);
  return el("div", { class: "fonte" }, img,
    el("div", {},
      el("p", {}, cita, " ", el("a", { href: d.url, target: "_blank", rel: "noopener", text: "@" + d.perfil, "aria-label": `Abrir publicação de @${d.perfil} em nova aba` })),
      el("p", { class: "num", text: `${fmt.pct(d.engajamento, 2)} de engajamento, ${fmt.lift(d.lift)} a mediana do perfil` }),
      el("p", { text: [rotulo(d.tipo_hook), rotulo(d.tema_principal)].join(", ") })));
}

function limparExplicacao(t) {
  let x = t.replace(/\s*\(filtros \{[^}]*\}\)/, "");
  for (const [k, v] of Object.entries(CAMPOS)) x = x.replaceAll(`${k} mais frequente = `, `${v.toLowerCase()} mais frequente é `);
  x = x.replace(/é ([A-Za-z_]+) \(/g, (_, v) => `é ${rotulo(v).toLowerCase()} (`);
  return x.replace(/Filtros relaxados por falta de dados: ([^.]*)\./, (_, f) => `Filtros retirados por falta de dados, ${f.replaceAll("_", " ")}.`);
}

function resumoDosAchados(s) {
  const vistos = new Set();
  const partes = [];
  for (const a of s.findings) {
    if (vistos.has(a.campo) || !CAMPOS[a.campo]) continue;
    vistos.add(a.campo);
    partes.push(`${CAMPOS[a.campo].toLowerCase()} mais frequente é ${rotulo(a.valor).toLowerCase()} (${fmt.pct(a.pct)})`);
  }
  return `Entre ${fmt.int(s.n_posts_analisados)} publicações de alto desempenho, ${partes.slice(0, 6).join("; ")}.`;
}

function blocoExplicacao(s, corpo, ctx) {
  const doModelo = s.mode !== "gerar_criativo" && corpo.texto_do_modelo;
  const titulo = s.mode === "recomendar" ? "Recomendações" : s.mode === "analisar" ? "Análise" : "Resumo do recorte";
  const texto = doModelo ? s.explanation : (s.explanation ? limparExplicacao(s.explanation) : resumoDosAchados(s));
  const corpoTexto = el("div", { class: doModelo ? "redigido" : "" }, ...texto.split(/\n{2,}/).map((p) => el("p", {}, textoComCitacoes(p, ctx))));
  const sec = el("section", { class: "bloco", "aria-labelledby": "exp-titulo" }, el("h3", { id: "exp-titulo", text: titulo }),
    el("div", { class: "bloco__corpo" }, corpoTexto));
  if (s.recomendacoes.length) {
    if (s.mode === "analisar") sec.append(el("h4", { class: "subtitulo", text: "Sugestões que saem da análise" }));
    sec.append(el("ol", { class: "recomendacoes redigido" }, ...s.recomendacoes.map((r) => el("li", {}, el("span", {}, textoComCitacoes(r, ctx))))));
  }
  sec.append(el("p", { class: "origem", text: doModelo
    ? "Texto redigido pelo modelo. Os números confiáveis estão no gráfico e na lista de publicações, que vêm da base"
    : "Resumo montado direto da base, sem o modelo" }));
  return sec;
}

function blocoReferencias(s, ctx) {
  const ol = el("ol", { class: "referencias" });
  s.reference_posts.forEach((p, i) => {
    const d = ctx.det[p.post_id] || {};
    const n = i + 1;
    const img = d.imagem
      ? el("img", { class: "ref__img", src: d.imagem, alt: `Capa da publicação de @${p.perfil}`, loading: "lazy", width: 72, height: 90 })
      : el("div", { class: "ref__img sem-imagem", text: "sem capa" });
    const chips = el("div", { class: "chips", "aria-label": "Categorias da rubrica" },
      chip("Tema", p.tema_principal), chip("Gancho", p.tipo_hook), p.formato_video ? chip("Formato", p.formato_video) : null,
      d.tom ? chip("Tom", d.tom) : null, d.tipo_cta ? chip("Chamada", d.tipo_cta) : null);
    ol.append(el("li", { class: "ref", id: `ref-${n}` },
      el("span", { class: "ref__n", "aria-hidden": "true", text: String(n) }),
      img,
      el("div", { class: "ref__corpo" },
        el("div", { class: "ref__titulo" },
          el("a", { href: p.url, target: "_blank", rel: "noopener", text: "@" + p.perfil, "aria-label": `Publicação ${n}, @${p.perfil}, abre em nova aba` }),
          el("span", { class: "ref__meta", text: `${rotulo(p.plataforma)}, ${rotulo(p.tipo_post).toLowerCase()}${d.publicado_em ? ", " + fmt.data(d.publicado_em) : ""}${d.faixa ? ", perfil " + rotulo(d.faixa).toLowerCase() : ""}` })),
        p.gancho ? el("p", { class: "ref__legenda" }, el("strong", { text: "Gancho " }), p.gancho) : null,
        chips),
      el("dl", { class: "ref__numeros" },
        el("dt", { text: "Engajamento" }), el("dd", { class: "forte", text: fmt.pct(p.engajamento, 2) }),
        el("dt", { text: "Vezes a mediana do perfil" }), el("dd", { text: fmt.lift(p.lift) }),
        el("dt", { text: "Curtidas" }), el("dd", { text: fmt.int(d.curtidas) }),
        el("dt", { text: "Comentários" }), el("dd", { text: fmt.int(d.comentarios) }),
        el("dt", { text: "Seguidores" }), el("dd", { text: fmt.int(d.seguidores) }))));
  });
  return el("section", { class: "bloco", "aria-labelledby": "ref-titulo" },
    el("h3", { id: "ref-titulo", text: "Publicações de referência" }),
    el("p", { class: "bloco__nota", text: "Publicações reais do top 10% mais próximas do pedido. Engajamento é (curtidas + comentários) ÷ seguidores. O número de cada uma é o mesmo usado nas citações acima." }),
    el("div", { class: "bloco__corpo" }, ol));
}

function chip(nome, valor) {
  if (valor == null) return null;
  return el("span", { class: "chip" }, el("span", { text: nome }), rotulo(valor));
}

// ------------------------------------------------------------------ gráfico de achados
function blocoAchados(s, exemplos) {
  const grupos = new Map();
  for (const a of s.findings) {
    if (!grupos.has(a.campo)) grupos.set(a.campo, []);
    grupos.get(a.campo).push(a);
  }
  const ordem = Object.keys(CAMPOS).filter((c) => grupos.has(c));
  const grade = el("div", { class: "achados" });
  for (const campo of ordem) grade.append(multiplo(CAMPOS[campo], grupos.get(campo), null, exemplos));
  const temFraco = s.findings.some((a) => a.confidence_flag);

  const tabela = el("div", { class: "tabela-rolagem", hidden: true },
    el("table", {}, el("caption", { text: "Achados do recorte em tabela" }),
      el("thead", {}, el("tr", {}, ...["Característica", "Valor", "Publicações", "Participação", "Confiança"].map((h, i) => el("th", { scope: "col", class: i > 1 && i < 4 ? "n" : null, text: h })))),
      el("tbody", {}, ...s.findings.map((a) => el("tr", {},
        el("td", { text: CAMPOS[a.campo] || a.campo }), el("td", { text: rotulo(a.valor) + (a.razao_top_base ? ` (${fmt.lift(a.razao_top_base)} a base)` : "") }),
        el("td", { class: "n", text: fmt.int(a.posts) }), el("td", { class: "n", text: fmt.pct(a.pct) }),
        el("td", { text: a.confidence_flag ? "Baixa, menos de 10 publicações" : "Adequada" }))))));
  const alterna = el("button", { type: "button", class: "botao botao--secundario tabela-alterna", "aria-expanded": "false", text: "Ver como tabela" });
  alterna.addEventListener("click", () => {
    const abrir = tabela.hidden;
    tabela.hidden = !abrir; grade.hidden = abrir;
    alterna.setAttribute("aria-expanded", abrir);
    alterna.textContent = abrir ? "Ver como gráfico" : "Ver como tabela";
  });

  return el("section", { class: "bloco", "aria-labelledby": "ach-titulo" },
    el("h3", { id: "ach-titulo", text: "O que mais se repete no recorte" }),
    el("p", { class: "bloco__nota", text: `As três categorias mais frequentes de cada característica da rubrica, entre as ${fmt.int(s.n_posts_analisados)} publicações analisadas. Clique numa barra para abrir as publicações que ela conta. São padrões observados, sem garantia de resultado.` }),
    el("div", { class: "bloco__corpo" }, grade, tabela),
    temFraco ? el("p", { class: "legenda-grafico" },
      el("span", {}, el("i", { class: "amostra", "aria-hidden": "true" }), "10 publicações ou mais"),
      el("span", {}, el("i", { class: "amostra amostra--fraca", "aria-hidden": "true" }), "Menos de 10 publicações, baixa confiança")) : null,
    alterna);
}

function multiplo(titulo, itens, total, exemplos) {
  return el("figure", { class: "achado", style: "margin:0" },
    titulo ? el("h4", {}, titulo, total ? el("small", { text: ` de ${fmt.int(total)}` }) : null) : null,
    el("ul", { class: "barras" }, ...itens.map((a) => {
      const extra = a.razao_top_base ? `, ${fmt.lift(a.razao_top_base)} a frequência na base` : "";
      const linha = [
        el("span", { class: "barra__nome", text: rotulo(a.valor) }),
        el("span", { class: "barra__trilho" },
          el("span", { class: "barra__area", "aria-hidden": "true" }, el("span", { class: "barra__marca", style: `width:${Math.max(a.pct * 100, 0.5)}%` })),
          el("span", { class: "barra__valor" }, el("strong", { text: fmt.pct(a.pct) }), ` ${fmt.int(a.posts)}`,
            el("span", { class: "sr", text: ` publicações${extra}${a.confidence_flag ? ", baixa confiança" : ""}` })))];
      const ex = exemplos?.[`${a.campo}|${a.valor}`];
      let li;
      if (ex?.length) {
        const lista = el("ul", { class: "barra__exemplos", hidden: true },
          ...ex.map((p) => el("li", {}, el("a", { href: p.url, target: "_blank", rel: "noopener", text: "@" + p.perfil, "aria-label": `Abrir publicação de @${p.perfil} em nova aba` }),
            el("span", { class: "num", text: ` ${fmt.pct(p.engajamento, 2)} de engajamento, ${fmt.lift(p.lift)} a mediana do perfil` }))));
        const bt = el("button", { type: "button", class: "barra barra--botao" + (a.confidence_flag ? " barra--fraca" : ""), "aria-expanded": "false" }, ...linha);
        bt.addEventListener("click", () => { const abrir = lista.hidden; lista.hidden = !abrir; bt.setAttribute("aria-expanded", abrir); });
        li = el("li", {}, bt, lista);
        dica(bt, () => [el("strong", { text: `${fmt.pct(a.pct)} ${rotulo(a.valor)}` }), el("br"), `${fmt.int(a.posts)} publicações${extra}`,
          a.confidence_flag ? el("br") : null, a.confidence_flag ? "Menos de 10 publicações, baixa confiança" : null, el("br"), "Clique para ver as publicações de maior desempenho"]);
      } else {
        li = el("li", { class: "barra" + (a.confidence_flag ? " barra--fraca" : "") }, ...linha);
        dica(li, () => [el("strong", { text: `${fmt.pct(a.pct)} ${rotulo(a.valor)}` }), el("br"), `${fmt.int(a.posts)} publicações${extra}`,
          a.confidence_flag ? el("br") : null, a.confidence_flag ? "Menos de 10 publicações, baixa confiança" : null]);
      }
      return li;
    })));
}

let tip;
function dica(alvo, conteudo) {
  const mostrar = (e) => {
    if (!tip) { tip = $("#tpl-tooltip").content.firstElementChild.cloneNode(true); document.body.append(tip); }
    tip.replaceChildren(...conteudo().filter(Boolean));
    tip.hidden = false;
    const r = alvo.getBoundingClientRect();
    const x = e?.clientX ?? r.left + r.width / 2;
    tip.style.left = Math.min(window.innerWidth - 270, x + 12) + "px";
    tip.style.top = r.top - tip.offsetHeight - 6 + "px";
  };
  alvo.addEventListener("pointermove", mostrar);
  alvo.addEventListener("pointerleave", () => tip && (tip.hidden = true));
}

// ------------------------------------------------------------------ visão da base
let base, basePronta = false, basePromessa = null;
function obterBase() {
  basePromessa ??= fetch("/api/base").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .catch((e) => { basePromessa = null; throw e; });
  return basePromessa;
}

// panorama exibido enquanto ainda não há consulta, com dados da base
async function carregarPanorama() {
  const alvo = $("#panorama");
  let b;
  try { b = await obterBase(); } catch { return; }
  // frequências calculadas a partir das publicações do top 10% (b.ranking), sem repetir o que já está na aba Visão da base
  const contar = (campo) => {
    const m = new Map();
    for (const r of b.ranking) if (r[campo] != null) m.set(r[campo], (m.get(r[campo]) || 0) + 1);
    const total = [...m.values()].reduce((s, v) => s + v, 0);
    return [...m].sort((x, y) => y[1] - x[1]).map(([valor, posts]) => ({ valor, posts, pct: posts / total }));
  };
  const grafico = (titulo, nota, lista) => el("section", { class: "bloco" }, el("h3", { text: titulo }), el("p", { class: "bloco__nota", text: nota }),
    el("div", { class: "bloco__corpo" }, multiplo("", lista.slice(0, 4).map((x) => ({ ...x, confidence_flag: x.posts < 10 })), null)));
  const destaques = b.ranking.filter((r) => r.imagem).slice(0, 6);
  const vitrine = el("section", { class: "bloco", "aria-labelledby": "vitrine-titulo" },
    el("h3", { id: "vitrine-titulo", text: "Quem mais superou o próprio perfil" }),
    el("p", { class: "bloco__nota", text: "Publicações do top 10% com maior engajamento em relação à mediana do próprio perfil. Clique para abrir a original." }),
    el("ul", { class: "vitrine bloco__corpo" }, ...destaques.map((r) => el("li", {},
      el("a", { href: r.url, target: "_blank", rel: "noopener", class: "vitrine__item", "aria-label": `Publicação de @${r.perfil}, ${fmt.pct(r.engajamento, 2)} de engajamento, abre em nova aba` },
        el("img", { src: r.imagem, alt: "", loading: "lazy", width: 160, height: 200 }),
        el("span", { class: "vitrine__lift", text: fmt.lift(r.lift) }),
        el("span", { class: "vitrine__perfil", text: "@" + r.perfil }),
        el("span", { class: "vitrine__meta", text: `${rotulo(r.tema_principal)}, ${fmt.pct(r.engajamento, 2)} de engajamento` }))))));
  alvo.replaceChildren(
    el("div", { class: "panorama__graficos" },
      grafico("Como abrem", "O gancho dos primeiros segundos.", b.hook),
      grafico("Como falam", "O tom da publicação.", contar("tom")),
      grafico("Como chamam", "A chamada para ação usada.", contar("tipo_cta"))),
    vitrine);
}

async function carregarBase() {
  if (basePronta) return;
  basePronta = true;
  const alvo = $("#base");
  try {
    base = await obterBase();
  } catch {
    basePronta = false;
    alvo.replaceChildren(aviso("erro", "A base não carregou", ["Confira se o terminal com o frontend continua aberto e abra a aba de novo."]));
    return;
  }
  const n = base.numeros;
  const numeros = el("dl", { class: "numeros" },
    el("div", {}, el("dt", { text: "publicações coletadas" }), el("dd", { text: fmt.int(n.publicacoes) })),
    el("div", {}, el("dt", { text: "com métrica válida" }), el("dd", { text: fmt.int(n.com_metrica) })),
    el("div", {}, el("dt", { text: "de alto desempenho categorizadas" }), el("dd", { text: fmt.int(n.top_categorizadas) })),
    el("div", {}, el("dt", { text: "perfis e canais" }), el("dd", { text: fmt.int(n.perfis) })),
    el("p", { class: "numeros__criterio", text: `${fmt.int(n.instagram)} publicações do Instagram e ${fmt.int(n.youtube)} Shorts, de ${fmt.data(n.inicio)} a ${fmt.data(n.fim)}. Alto desempenho é o top 10% por plataforma do engajamento dividido pela mediana do próprio perfil.` }));

  const freq = (titulo, lista, total, nota) => el("section", { class: "bloco" }, el("h3", { text: titulo }), el("p", { class: "bloco__nota", text: nota }),
    el("div", { class: "bloco__corpo" }, multiplo("", lista.map((x) => ({ ...x, confidence_flag: x.posts < 10 })), null)));

  alvo.replaceChildren(
    el("h2", { class: "sr", text: "Visão da base" }),
    numeros,
    el("div", { class: "base__duas" },
      freq("Temas no top 10%", base.tema, n.top_categorizadas, `Entre as ${fmt.int(n.top_categorizadas)} publicações de alto desempenho categorizadas.`),
      freq("Formatos de vídeo no top 10%", base.formato, base.n_video, `Entre as ${fmt.int(base.n_video)} publicações em vídeo do top 10%.`)),
    blocoRanking(),
    blocoPerfis());
}

function blocoRanking() {
  let ordem = "lift", plataforma = "", tema = "", limite = 25;
  const corpo = el("tbody");
  const mais = el("button", { type: "button", class: "botao botao--secundario mais", text: "Mostrar mais 25" });
  const contagem = el("p", { class: "ajuda", "aria-live": "polite" });
  const cab = (chave, texto) => {
    const th = el("th", { scope: "col", class: "n" }, el("button", { type: "button", text: texto, onclick: () => { ordem = chave; limite = 25; desenhar(); } }));
    th.dataset.chave = chave;
    return th;
  };
  const thead = el("thead", {}, el("tr", {},
    el("th", { scope: "col", text: "Posição" }), el("th", { scope: "col", text: "Capa" }), el("th", { scope: "col", text: "Perfil" }),
    el("th", { scope: "col", text: "Tipo" }), el("th", { scope: "col", text: "Tema" }), el("th", { scope: "col", text: "Gancho" }),
    cab("engajamento", "Engajamento"), cab("lift", "Vezes a mediana do perfil")));

  function desenhar() {
    for (const th of $$("th[data-chave]", thead)) th.toggleAttribute("aria-sort", th.dataset.chave === ordem), th.dataset.chave === ordem && th.setAttribute("aria-sort", "descending");
    const linhas = base.ranking.filter((r) => (!plataforma || r.plataforma === plataforma) && (!tema || r.tema_principal === tema))
      .sort((a, b) => (b[ordem] ?? 0) - (a[ordem] ?? 0));
    corpo.replaceChildren(...linhas.slice(0, limite).map((r, i) => el("tr", {},
      el("td", { class: "n", text: String(i + 1) }),
      el("td", {}, r.imagem ? el("img", { class: "mini", src: r.imagem, alt: "", loading: "lazy", width: 36, height: 45 }) : ""),
      el("td", {}, el("a", { href: r.url, target: "_blank", rel: "noopener", text: "@" + r.perfil, "aria-label": `Abrir publicação ${i + 1}, @${r.perfil}, em nova aba` })),
      el("td", { text: rotulo(r.tipo_post) }),
      el("td", { text: rotulo(r.tema_principal) }), el("td", { text: rotulo(r.tipo_hook) }),
      el("td", { class: "n", text: fmt.pct(r.engajamento, 2) }), el("td", { class: "n", text: fmt.lift(r.lift) }))));
    contagem.textContent = `${Math.min(limite, linhas.length)} de ${linhas.length} publicações, ordenadas por ${ordem === "lift" ? "vezes a mediana do perfil" : "engajamento"}`;
    mais.hidden = limite >= linhas.length;
  }
  mais.addEventListener("click", () => { limite += 25; desenhar(); });

  const selPlat = el("select", { id: "rk-plat" }, el("option", { value: "", text: "Todas" }), el("option", { value: "instagram", text: "Instagram" }), el("option", { value: "youtube", text: "YouTube Shorts" }));
  selPlat.addEventListener("change", () => { plataforma = selPlat.value; limite = 25; desenhar(); });
  const temas = [...new Set(base.ranking.map((r) => r.tema_principal).filter(Boolean))].sort();
  const selTema = el("select", { id: "rk-tema" }, el("option", { value: "", text: "Todos" }), ...temas.map((t) => el("option", { value: t, text: rotulo(t) })));
  selTema.addEventListener("change", () => { tema = selTema.value; limite = 25; desenhar(); });

  desenhar();
  return el("section", { class: "bloco", "aria-labelledby": "rk-titulo" },
    el("h3", { id: "rk-titulo", text: "Ranking do top 10%" }),
    el("p", { class: "bloco__nota", text: "Clique no título de uma coluna numérica para ordenar. O link abre a publicação original." }),
    el("div", { class: "ranking-filtros" },
      el("div", { class: "campo" }, el("label", { for: "rk-plat", text: "Plataforma" }), selPlat),
      el("div", { class: "campo" }, el("label", { for: "rk-tema", text: "Tema" }), selTema),
      contagem),
    el("div", { class: "bloco__corpo tabela-rolagem" }, el("table", {}, el("caption", { class: "sr", text: "Ranking das publicações de alto desempenho" }), thead, corpo)),
    mais);
}

function blocoPerfis() {
  const lista = base.perfis_destaque.slice(0, 15);
  return el("section", { class: "bloco", "aria-labelledby": "pf-titulo" },
    el("h3", { id: "pf-titulo", text: "Perfis em destaque" }),
    el("p", { class: "bloco__nota", text: "Perfis com mais publicações no top 10% e o que predomina nelas." }),
    el("div", { class: "bloco__corpo tabela-rolagem" }, el("table", {},
      el("caption", { class: "sr", text: "Perfis em destaque" }),
      el("thead", {}, el("tr", {}, ...["Perfil", "Plataforma", "Tamanho", "Publicações no topo", "Mediana de vezes a mediana do perfil", "Tema", "Formato"].map((h, i) => el("th", { scope: "col", class: i === 3 || i === 4 ? "n" : null, text: h })))),
      el("tbody", {}, ...lista.map((p) => el("tr", {},
        el("td", {}, el("strong", { text: "@" + p.perfil })), el("td", { text: rotulo(p.plataforma) }), el("td", { text: rotulo(p.faixa) }),
        el("td", { class: "n", text: fmt.int(p.posts_top) }), el("td", { class: "n", text: fmt.lift(p.lift_mediano) }),
        el("td", { text: rotulo(p.tema_predominante) }), el("td", { text: rotulo(p.formato_predominante) })))))));
}

// ------------------------------------------------------------------ início
iniciarAbas();
carregarExemplos();
carregarPanorama();
form.addEventListener("change", (e) => {
  if (e.target.name === "mode") atualizarModo();
  if (FILTROS.includes(e.target.name)) atualizarResumoFiltros();
});
form.addEventListener("submit", (e) => { e.preventDefault(); consultar(); });
form.elements.query.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) consultar(); });
atualizarModo();
