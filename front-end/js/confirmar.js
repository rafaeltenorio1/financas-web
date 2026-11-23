import { el, icone } from "./dom.js";

export function confirmar({ titulo, texto = "", confirmar: rotuloSim = "Confirmar", cancelar: rotuloNao = "Cancelar", perigo = false }) {
  return new Promise((resolver) => {
    const origem = document.activeElement;
    let resposta = false;
    const sim = el("button", { type: "button", class: `btn ${perigo ? "btn-perigo" : "btn-primario"}`, texto: rotuloSim });
    const nao = el("button", { type: "button", class: "btn btn-secundario", texto: rotuloNao });
    const dialogo = el(
      "dialog",
      { class: "confirmacao", role: "alertdialog", "aria-labelledby": "confirmacao-titulo", "aria-describedby": texto ? "confirmacao-texto" : null },
      el(
        "div",
        { class: `confirmacao-caixa${perigo ? " perigo" : ""}` },
        el("span", { class: "confirmacao-icone", "aria-hidden": "true" }, icone(perigo ? "alerta" : "info")),
        el("h2", { id: "confirmacao-titulo", texto: titulo }),
        texto ? el("p", { id: "confirmacao-texto", texto }) : null,
        el("div", { class: "confirmacao-botoes" }, nao, sim),
      ),
    );
    sim.addEventListener("click", () => {
      resposta = true;
      dialogo.close();
    });
    nao.addEventListener("click", () => dialogo.close());
    dialogo.addEventListener("click", (evento) => {
      if (evento.target === dialogo) dialogo.close();
    });
    dialogo.addEventListener("close", () => {
      dialogo.remove();
      if (origem?.isConnected) origem.focus();
      resolver(resposta);
    });
    document.body.append(dialogo);
    dialogo.showModal();
    (perigo ? nao : sim).focus();
  });
}
