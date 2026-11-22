import { el } from "../../dom.js";
import { moeda, moedaCurta } from "../../formatos.js";
import { categoriasDoTipo, mesesDoHistorico } from "../calculos.js";
import { cabecalho, corDaLinha } from "../componentes.js";

const SVG = "http://www.w3.org/2000/svg";
const PERIODOS = [
  [2, "Mês passado"],
  [3, "3 meses"],
  [12, "12 meses"],
];
const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });
const mesCurto = new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" });
const dataDoMes = ({ ano, mes }) => new Date(Date.UTC(ano, mes - 1, 15));

function svg(tag, atributos = {}, texto) {
  const elemento = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(atributos)) elemento.setAttribute(k, v);
  if (texto !== undefined) elemento.textContent = texto;
  return elemento;
}

function media(meses, campo) {
  const anteriores = meses.filter((m) => !m.atual && (m.receitas > 0 || m.despesas > 0));
  return anteriores.length ? anteriores.reduce((s, m) => s + m[campo], 0) / anteriores.length : null;
}

function mostrarDica(alvo, dica, barra, mes, tipo, mediaTipo) {
  const valor = tipo === "despesa" ? mes.despesas : mes.receitas;
  const rotulo = tipo === "despesa" ? "Gastos" : "Ganhos";
  dica.replaceChildren(
    el("p", { class: "dica-titulo", texto: `${rotulo}, ${nomeDoMes.format(dataDoMes(mes))} de ${mes.ano}${mes.atual ? " (até agora)" : ""}` }),
    el("p", { class: "dica-valor num", texto: moeda(valor) }),
  );
  if (mediaTipo !== null) {
    const diferenca = valor - mediaTipo;
    dica.append(el("p", { class: "dica-sub", texto: `${moeda(Math.abs(diferenca))} ${diferenca >= 0 ? "acima" : "abaixo"} da sua média` }));
  }
  const linhas = categoriasDoTipo(mes.categorias, tipo, 4);
  if (linhas.length) {
    const lista = el("ul");
    for (const linha of linhas) {
      const item = el("li", {}, el("i"), el("span", { texto: linha.nome ?? "Sem categoria" }), el("span", { class: "num", texto: moeda(linha.total) }));
      item.style.setProperty("--cor", corDaLinha(linha));
      lista.append(item);
    }
    dica.append(lista);
  }
  dica.hidden = false;
  const caixa = alvo.getBoundingClientRect();
  const marca = barra.getBoundingClientRect();
  const largura = dica.offsetWidth;
  const x = Math.max(0, Math.min(marca.left - caixa.left + marca.width / 2 - largura / 2, caixa.width - largura));
  const acima = marca.top - dica.offsetHeight - 8 > 8;
  dica.style.left = `${x}px`;
  dica.style.top = `${acima ? marca.top - caixa.top - dica.offsetHeight - 8 : marca.bottom - caixa.top + 8}px`;
}

function desenhar(alvo, nota, tabela, meses) {
  alvo.replaceChildren();
  const muitos = meses.length > 3;
  const largura = Math.max(260, alvo.clientWidth || 520);
  const altura = muitos ? 176 : 196;
  const base = 132;
  const topo = 8;
  const maximo = Math.max(1, ...meses.flatMap((m) => [m.receitas, m.despesas]));
  const passo = largura / meses.length;
  const barraLargura = Math.min(48, passo * (muitos ? 0.36 : 0.24));
  const mediaGastos = media(meses, "despesas");
  const mediaGanhos = media(meses, "receitas");
  const grafico = svg("svg", { viewBox: `0 0 ${largura} ${altura}`, role: "group", "aria-label": "Ganhos e gastos por mês" });
  for (const fracao of [0, 0.5, 1]) {
    const y = base - fracao * (base - topo);
    grafico.append(svg("line", { class: "grade", x1: 0, x2: largura, y1: y, y2: y }));
  }
  const dica = el("div", { class: "dica", hidden: true, id: `dica-${alvo.dataset.id}`, role: "tooltip" });
  const fechar = () => (dica.hidden = true);
  meses.forEach((mes, i) => {
    const centro = passo * i + passo / 2;
    for (const [tipo, cor, lado] of [["receita", "var(--receita)", -1], ["despesa", "var(--despesa)", 1]]) {
      const valor = tipo === "receita" ? mes.receitas : mes.despesas;
      const altBarra = Math.max(4, (valor / maximo) * (base - topo));
      const x = lado < 0 ? centro - barraLargura - 1 : centro + 1;
      const rotulo = `${tipo === "receita" ? "Ganhos" : "Gastos"} em ${nomeDoMes.format(dataDoMes(mes))} de ${mes.ano}: ${moeda(valor)}`;
      const grupo = svg("g", { class: "barra", tabindex: "0", role: "img", "aria-label": rotulo, "aria-describedby": dica.id });
      grupo.append(
        svg("rect", { x: x - 2, y: topo, width: barraLargura + 4, height: base - topo, fill: "transparent" }),
        svg("path", { d: `M${x},${base} v${-(altBarra - 4)} q0,-4 4,-4 h${barraLargura - 8} q4,0 4,4 v${altBarra - 4} z`, fill: cor }),
      );
      const abrir = () => mostrarDica(alvo, dica, grupo, mes, tipo, tipo === "despesa" ? mediaGastos : mediaGanhos);
      grupo.addEventListener("pointerenter", abrir);
      grupo.addEventListener("focus", abrir);
      grupo.addEventListener("click", abrir);
      grupo.addEventListener("pointerleave", fechar);
      grupo.addEventListener("blur", fechar);
      grupo.addEventListener("keydown", (evento) => evento.key === "Escape" && fechar());
      grafico.append(grupo);
    }
    const nome = muitos ? mesCurto.format(dataDoMes(mes)).replace(".", "") : `${nomeDoMes.format(dataDoMes(mes))}${mes.atual && passo >= 150 ? " (até agora)" : ""}`;
    grafico.append(svg("text", { x: centro, y: base + 20, "text-anchor": "middle", "aria-hidden": "true" }, nome));
    if (muitos) {
      if (i === 0 || mes.mes === 1) grafico.append(svg("text", { class: "ano", x: passo * i + 2, y: base + 40, "aria-hidden": "true" }, String(mes.ano)));
    } else {
      grafico.append(svg("text", { class: "valor", x: centro, y: base + 40, "text-anchor": "middle", "aria-hidden": "true" }, `+ ${moedaCurta(mes.receitas)}`));
      grafico.append(svg("text", { class: "valor", x: centro, y: base + 58, "text-anchor": "middle", "aria-hidden": "true" }, `− ${moedaCurta(mes.despesas)}`));
    }
  });
  alvo.append(grafico, dica);

  const atual = meses.at(-1);
  const anterior = meses.at(-2);
  nota.replaceChildren();
  if (meses.length === 2) {
    const diferenca = anterior.despesas - atual.despesas;
    nota.append(
      `${atual.atual ? "Até agora você" : "Você"} gastou `,
      el("strong", { texto: `${moeda(Math.abs(diferenca))} ${diferenca >= 0 ? "a menos" : "a mais"}` }),
      ` que em ${nomeDoMes.format(dataDoMes(anterior))}.`,
    );
  } else if (mediaGastos !== null) {
    nota.append("Média de gastos nos meses anteriores do período: ", el("strong", { texto: moeda(mediaGastos) }), ".");
  }

  tabela.replaceChildren(
    el("caption", { texto: "Ganhos e gastos por mês" }),
    el("thead", {}, el("tr", {}, el("th", { scope: "col", texto: "Mês" }), el("th", { scope: "col", texto: "Ganhos" }), el("th", { scope: "col", texto: "Gastos" }))),
    el(
      "tbody",
      {},
      meses.map((m) =>
        el("tr", {}, el("th", { scope: "row", texto: `${nomeDoMes.format(dataDoMes(m))} de ${m.ano}` }), el("td", { texto: moeda(m.receitas) }), el("td", { texto: moeda(m.despesas) })),
      ),
    ),
  );
}

export default {
  id: "meses",
  titulo: "Comparação com meses anteriores",
  montar(cartao, { dados, mes, preferencias, alterarPreferencias, aoDesmontar }) {
    const segmentos = el("div", { class: "segmentos", role: "group", "aria-label": "Período do gráfico" });
    for (const [quantidade, rotulo] of PERIODOS) {
      const botao = el("button", { type: "button", "aria-pressed": String(preferencias.periodo_meses === quantidade), texto: rotulo });
      botao.addEventListener("click", () => {
        if (preferencias.periodo_meses !== quantidade) alterarPreferencias({ periodo_meses: quantidade });
      });
      segmentos.append(botao);
    }
    cabecalho(cartao, "Comparação com meses anteriores", segmentos);
    const legenda = el("div", { class: "legenda", "aria-hidden": "true" });
    for (const [rotulo, cor] of [["Ganhos", "var(--receita)"], ["Gastos", "var(--despesa)"]]) {
      const marcador = el("i");
      marcador.style.background = cor;
      legenda.append(el("span", {}, marcador, rotulo));
    }
    const alvo = el("div", { class: "grafico" });
    alvo.dataset.id = cartao.dataset.id;
    const nota = el("p", { class: "grafico-nota" });
    const tabela = el("table");
    cartao.append(legenda, alvo, nota, el("div", { class: "sr" }, tabela));

    const meses = mesesDoHistorico(dados.historico, mes, preferencias.periodo_meses);
    let largura = 0;
    const observador = new ResizeObserver(([entrada]) => {
      const nova = Math.round(entrada.contentRect.width);
      if (nova && nova !== largura) {
        largura = nova;
        desenhar(alvo, nota, tabela, meses);
      }
    });
    observador.observe(alvo);
    aoDesmontar(() => observador.disconnect());
  },
};
