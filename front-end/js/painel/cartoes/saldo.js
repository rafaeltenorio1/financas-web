import { el } from "../../dom.js";
import { moeda } from "../../formatos.js";
import { saldo } from "../calculos.js";

export default {
  id: "saldo",
  titulo: "Saldo do mês",
  montar(cartao, { dados }) {
    const valores = saldo(dados.resumo);
    cartao.classList.add("saldo");
    const id = `titulo-${cartao.dataset.id}`;
    cartao.setAttribute("aria-labelledby", id);
    cartao.append(
      el("h2", { class: "saldo-rotulo", id, texto: "Saldo do mês" }),
      el("p", { class: `saldo-valor num${valores.saldo < 0 ? " negativo" : ""}`, texto: moeda(valores.saldo) }),
    );
    if (valores.gastoPct === null) {
      cartao.append(el("p", { class: "saldo-frase", texto: valores.despesas > 0 ? "Nenhum ganho registrado neste mês." : "Nenhuma transação neste mês." }));
      return;
    }
    const frase = el("p", { class: "saldo-frase" });
    if (valores.guardadoPct >= 0) frase.append("Você guardou ", el("strong", { texto: `${valores.guardadoPct}%` }), " do que ganhou.");
    else frase.append("Você gastou ", el("strong", { texto: moeda(valores.despesas - valores.receitas) }), " a mais do que ganhou.");
    const preenchido = el("span");
    preenchido.style.width = `${Math.min(valores.gastoPct, 100)}%`;
    cartao.append(
      frase,
      el(
        "div",
        { class: "medidor" },
        el("div", { class: "medidor-trilho", role: "img", "aria-label": `Os gastos são ${valores.gastoPct}% dos ganhos` }, preenchido),
        el("div", { class: "medidor-legenda", "aria-hidden": "true" }, el("span", { texto: `Gastos: ${valores.gastoPct}% dos ganhos` }), el("span", { texto: "100%" })),
      ),
    );
  },
};
