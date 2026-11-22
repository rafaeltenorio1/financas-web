import { el, icone } from "../../dom.js";
import { chaveDoMes } from "../../datas.js";
import { moeda } from "../../formatos.js";
import { cabecalho, link, linhaDaTransacao, vazio } from "../componentes.js";

const MODOS = [
  ["lista", "layout-lista", "Lista única"],
  ["colunas", "layout-colunas", "Gastos e ganhos separados"],
];

function lista(transacoes, classe = "") {
  return el("ul", { class: `tx-lista ${classe}` }, transacoes.map(linhaDaTransacao));
}

export default {
  id: "transacoes",
  titulo: "Transações",
  montar(cartao, { dados, mes, preferencias, alterarPreferencias }) {
    cartao.classList.add("cartao-transacoes");
    const troca = el("div", { class: "troca", role: "group", "aria-label": "Como mostrar as transações" });
    for (const [modo, simbolo, rotulo] of MODOS) {
      const botao = el("button", { type: "button", title: rotulo, "aria-pressed": String(preferencias.lista_transacoes === modo) }, icone(simbolo), el("span", { class: "sr", texto: rotulo }));
      botao.addEventListener("click", () => {
        if (preferencias.lista_transacoes !== modo) alterarPreferencias({ lista_transacoes: modo });
      });
      troca.append(botao);
    }
    cabecalho(cartao, "Transações", link("Ver todas", `#/transacoes?mes=${chaveDoMes(mes)}`, "Ver todas as transações do mês"), troca);

    const despesas = dados.despesas ?? [];
    const receitas = dados.receitas ?? [];
    if (!despesas.length && !receitas.length) {
      cartao.append(vazio("Nenhuma transação neste mês.", { href: "#/nova", texto: "Registrar transação" }));
      return;
    }

    if (preferencias.lista_transacoes === "lista") {
      const todas = [...despesas, ...receitas].sort((a, b) => b.data_hora.localeCompare(a.data_hora)).slice(0, 10);
      cartao.append(lista(todas, "lista-unica"));
      return;
    }

    const abas = el("div", { class: "abas", role: "tablist", "aria-label": "Tipo de transação" });
    const colunas = el("div", { class: "colunas" });
    const grupos = [
      ["despesa", "Gastos", "sai", dados.resumo?.despesas ?? 0, despesas, "Nenhum gasto neste mês."],
      ["receita", "Ganhos", "entra", dados.resumo?.receitas ?? 0, receitas, "Nenhum ganho neste mês."],
    ];
    const botoes = [];
    grupos.forEach(([tipo, rotulo, simbolo, total, itens, textoVazio], i) => {
      const idAba = `aba-${tipo}-${cartao.dataset.id}`;
      const idColuna = `coluna-${tipo}-${cartao.dataset.id}`;
      const aba = el(
        "button",
        { type: "button", class: `aba aba-${tipo}`, role: "tab", id: idAba, "aria-controls": idColuna, "aria-selected": String(i === 0), tabindex: i === 0 ? "0" : "-1" },
        el("span", { class: "aba-rotulo" }, icone(simbolo, "ic-sm"), rotulo),
        el("span", { class: "aba-valor num", texto: moeda(total) }),
      );
      const coluna = el(
        "div",
        { class: `coluna${i === 0 ? "" : " oculta"}`, id: idColuna, role: "tabpanel", "aria-labelledby": idAba },
        el("div", { class: `coluna-total tx-${tipo}` }, el("p", {}, icone(simbolo, "ic-sm"), rotulo), el("p", { class: "num tx-valor", texto: moeda(total) })),
        itens.length ? lista(itens.slice(0, 6)) : vazio(textoVazio),
      );
      botoes.push([aba, coluna]);
      abas.append(aba);
      colunas.append(coluna);
    });
    const selecionar = (indice, focar) => {
      botoes.forEach(([aba, coluna], i) => {
        aba.setAttribute("aria-selected", String(i === indice));
        aba.tabIndex = i === indice ? 0 : -1;
        coluna.classList.toggle("oculta", i !== indice);
      });
      if (focar) botoes[indice][0].focus();
    };
    botoes.forEach(([aba], i) => {
      aba.addEventListener("click", () => selecionar(i));
      aba.addEventListener("keydown", (evento) => {
        if (evento.key === "ArrowRight" || evento.key === "ArrowLeft") {
          evento.preventDefault();
          selecionar(1 - i, true);
        }
      });
    });
    cartao.append(abas, colunas);
  },
};
