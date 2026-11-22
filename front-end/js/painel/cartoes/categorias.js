import { el } from "../../dom.js";
import { chaveDoMes } from "../../datas.js";
import { moeda } from "../../formatos.js";
import { categoriasDoTipo } from "../calculos.js";
import { cabecalho, corDaLinha, iconeDaCategoria, link, vazio } from "../componentes.js";

function cartaoDeCategorias(id, titulo, tipo, textoVazio) {
  return {
    id,
    titulo,
    montar(cartao, { dados, mes }) {
      cabecalho(cartao, titulo, link("Ver todas", `#/transacoes?mes=${chaveDoMes(mes)}&tipo=${tipo}`, tipo === "despesa" ? "Ver todos os gastos do mês" : "Ver todos os ganhos do mês"));
      const linhas = categoriasDoTipo(dados.resumo?.por_categoria, tipo, 5);
      if (!linhas.length) {
        cartao.append(vazio(textoVazio));
        return;
      }
      const total = linhas.reduce((s, c) => s + c.total, 0);
      const maior = Math.max(...linhas.map((c) => c.total));
      const lista = el("ul", { class: "categorias" });
      for (const linha of linhas) {
        const barra = el("span");
        barra.style.width = `${(linha.total / maior) * 100}%`;
        const item = el(
          "li",
          {},
          iconeDaCategoria(linha),
          el("span", { class: "categoria-nome", texto: linha.nome ?? "Sem categoria", title: linha.nome ?? "Sem categoria" }),
          el("span", { class: "categoria-valor num" }, moeda(linha.total), el("span", { class: "categoria-pct", texto: `${Math.round((linha.total / total) * 100)}%` })),
          el("span", { class: "categoria-trilho", "aria-hidden": "true" }, barra),
        );
        item.style.setProperty("--cor", corDaLinha(linha));
        lista.append(item);
      }
      cartao.append(lista);
    },
  };
}

export const gastosPorCategoria = cartaoDeCategorias("categorias", "Para onde foi o dinheiro", "despesa", "Nenhum gasto neste mês.");
export const ganhosPorCategoria = cartaoDeCategorias("origem", "De onde veio o dinheiro", "receita", "Nenhum ganho neste mês.");
