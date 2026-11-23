import { el, icone, mensagem, ocupado } from "../../dom.js";
import { dataCurta, moeda } from "../../formatos.js";
import { NUMEROS, calcularNumero } from "../calculos.js";
import { NUMEROS as ORDEM } from "../preferencias.js";
import { cabecalho } from "../componentes.js";

function abrirEscolha(preferencias, salvarAgora) {
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const caixas = ORDEM.map((id) => el("input", { type: "checkbox", name: "numero", value: id, checked: preferencias.numeros.includes(id) }));
  const salvar = el("button", { type: "submit", class: "btn btn-primario", texto: "Salvar" });
  const cancelar = el("button", { type: "button", class: "btn btn-secundario", texto: "Cancelar" });
  const formulario = el(
    "form",
    { method: "dialog" },
    el("h2", { id: "titulo-escolher-numeros", texto: "Escolher números" }),
    el("p", { texto: "Marque o que você quer ver no cartão." }),
    el("fieldset", {}, el("legend", { class: "sr", texto: "Números do cartão" }), ORDEM.map((id, i) => el("label", { class: "marcar" }, caixas[i], NUMEROS[id].rotulo))),
    aviso,
    el("div", { class: "dialogo-rodape" }, cancelar, salvar),
  );
  const dialogo = el("dialog", { class: "dialogo", "aria-labelledby": "titulo-escolher-numeros" }, formulario);
  cancelar.addEventListener("click", () => dialogo.close());
  dialogo.addEventListener("close", () => dialogo.remove());
  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const marcados = caixas.filter((c) => c.checked).map((c) => c.value);
    ocupado(salvar, true, "Salvando…");
    try {
      await salvarAgora({ numeros: marcados });
      dialogo.close();
    } catch (erro) {
      mensagem(aviso, "erro", erro.message);
    } finally {
      ocupado(salvar, false);
    }
  });
  document.body.append(dialogo);
  dialogo.showModal();
}

export default {
  id: "numeros",
  titulo: "Outros números do mês",
  montar(cartao, { dados, contexto, preferencias, salvarAgora }) {
    const escolher = el("button", { type: "button", class: "cartao-botao" }, icone("ajustes", "ic-sm"), "Escolher");
    escolher.addEventListener("click", () => abrirEscolha(preferencias, salvarAgora));
    cabecalho(cartao, "Outros números do mês", escolher);
    if (!preferencias.numeros.length) {
      cartao.append(el("p", { class: "cartao-vazio", texto: "Nenhum número escolhido. Use Escolher para adicionar." }));
      return;
    }
    const base = { resumo: dados.resumo, historico: dados.historico, contas: dados.contas, contexto };
    const lista = el("dl", { class: "numeros" });
    for (const id of preferencias.numeros) {
      const resultado = calcularNumero(id, base);
      const item = el("div", { class: `numero${resultado.indisponivel ? " indisponivel" : ""}` }, el("dt", { texto: NUMEROS[id].rotulo }));
      if (resultado.indisponivel) {
        item.append(el("dd", { texto: resultado.indisponivel }));
      } else {
        const detalhe = resultado.data ? `${resultado.detalhe}, ${dataCurta(resultado.data)}` : resultado.detalhe;
        item.append(el("dd", { class: "num" }, resultado.texto ? resultado.texto : el("span", { "data-valor": resultado.valor, texto: moeda(resultado.valor) }), el("small", { texto: detalhe })));
      }
      lista.append(item);
    }
    cartao.append(lista);
  },
};
