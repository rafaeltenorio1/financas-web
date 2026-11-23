import { el, icone } from "../dom.js";
import { categoria, corDaCategoria, iconeValido, simboloDaCategoria } from "../categorias.js";
import { marcaDe, marcaPorId } from "../marcas.js";
import { iconeDaContaRecorrente } from "../contas-icones.js";
import { dataCurta, moedaComSinal } from "../formatos.js";

const SVG = "http://www.w3.org/2000/svg";

export function cabecalho(cartao, titulo, ...acoes) {
  const id = `titulo-${cartao.dataset.id}`;
  cartao.setAttribute("aria-labelledby", id);
  const cab = el("div", { class: "cartao-cab" }, el("h2", { id, texto: titulo }));
  if (acoes.length) cab.append(el("div", { class: "cartao-acoes" }, ...acoes));
  cartao.append(cab);
  return cab;
}

export function link(texto, href, rotulo) {
  return el("a", { class: "cartao-link", href, texto, "aria-label": rotulo });
}

export function vazio(texto, acao) {
  const p = el("p", { class: "cartao-vazio", texto });
  if (acao) p.append(" ", el("a", { href: acao.href, texto: acao.texto }));
  return p;
}

export function esqueleto() {
  return el(
    "div",
    { class: "cartao-esqueleto", "aria-hidden": "true" },
    el("span", { class: "esqueleto" }),
    el("span", { class: "esqueleto" }),
    el("span", { class: "esqueleto" }),
    el("span", { class: "esqueleto" }),
  );
}

export function erroDoCartao(titulo, aoTentar) {
  const botao = el("button", { type: "button", class: "btn btn-secundario", texto: "Tentar de novo" });
  botao.addEventListener("click", aoTentar);
  return el(
    "div",
    { class: "cartao-erro", role: "alert" },
    el("p", { class: "cartao-vazio", texto: `Não foi possível carregar ${titulo.toLowerCase()}.` }),
    botao,
  );
}

function svgDeUso(href, classe) {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  if (classe) svg.setAttribute("class", classe);
  const uso = document.createElementNS(SVG, "use");
  uso.setAttribute("href", href);
  svg.append(uso);
  return svg;
}

export function caixaDaMarca(marca) {
  const caixa = el("span", { class: `tx-icone ${marca.estilo}`, "aria-hidden": "true" });
  caixa.style.background = marca.fundo;
  caixa.style.color = marca.cor;
  if (marca.estilo === "monograma") {
    caixa.textContent = marca.texto;
    if (marca.texto.length > 2) caixa.classList.add("longo");
  } else {
    caixa.append(svgDeUso(`img/marcas.svg#${marca.id}`));
  }
  return caixa;
}

export function caixaDoSimbolo(simbolo, cat) {
  const caixa = el("span", { class: "tx-icone categoria", "aria-hidden": "true" }, icone(simbolo));
  caixa.style.setProperty("--cor", corDaCategoria(cat));
  return caixa;
}

export function iconePorCodigo(codigo, cat = null) {
  if (typeof codigo !== "string") return null;
  if (codigo.startsWith("m-")) {
    const marca = marcaPorId(codigo.slice(2));
    return marca ? caixaDaMarca(marca) : null;
  }
  return iconeValido(codigo) ? caixaDoSimbolo(codigo, cat) : null;
}

export function iconeDaTransacao(transacao) {
  const cat = categoria(transacao.id_categoria);
  const escolhido = iconePorCodigo(transacao.icone ?? iconeDaContaRecorrente(transacao.id_conta_recorrente), cat);
  if (escolhido) return escolhido;
  const marca = marcaDe(transacao.nome);
  if (marca) return caixaDaMarca(marca);
  return caixaDoSimbolo(simboloDaCategoria(cat), cat);
}

export function nomeDaTransacao(transacao) {
  return transacao.nome?.trim() || categoria(transacao.id_categoria)?.nome || "Sem descrição";
}

export function linhaDaTransacao(transacao) {
  const cat = categoria(transacao.id_categoria);
  const meta = [cat?.nome ?? "Sem categoria", dataCurta(transacao.data_hora)].join(", ");
  return el(
    "li",
    { class: `tx tx-${transacao.tipo}` },
    el(
      "a",
      { href: `#/transacoes?id=${encodeURIComponent(transacao.id_transacao)}` },
      iconeDaTransacao(transacao),
      el("span", { class: "tx-info" }, el("span", { class: "tx-nome", texto: nomeDaTransacao(transacao), title: nomeDaTransacao(transacao) }), el("span", { class: "tx-meta", texto: meta })),
      el("span", { class: "sr", texto: transacao.tipo === "receita" ? "Receita" : "Despesa" }),
      el("span", { class: "tx-valor num", texto: moedaComSinal(transacao.valor, transacao.tipo) }),
    ),
  );
}

export function iconeDaCategoria(linha) {
  const cat = linha.outras ? null : categoria(linha.id_categoria);
  const simbolo = linha.outras ? "c-generica" : simboloDaCategoria(cat ?? (linha.nome ? { nome: linha.nome } : null));
  const caixa = el("span", { class: "categoria-icone", "aria-hidden": "true" }, icone(simbolo));
  return caixa;
}

export function corDaLinha(linha) {
  if (linha.outras || !linha.id_categoria) return "var(--cat-outras)";
  return corDaCategoria(categoria(linha.id_categoria) ?? { cor: linha.cor });
}
