import { el, icone } from "./dom.js";

let regiao = null;

function obterRegiao() {
  if (!regiao || !regiao.isConnected) {
    regiao = el("div", { class: "avisos", role: "status", "aria-live": "polite" });
    document.body.append(regiao);
  }
  return regiao;
}

export function avisar(texto, { acao, duracao = 6000, tipo = "sucesso" } = {}) {
  const caixa = el("div", { class: `aviso-flutuante aviso-${tipo}` }, icone(tipo === "erro" ? "erro" : "sucesso", "ic-sm"), el("span", { texto }));
  let temporizador = null;
  const fechar = () => {
    clearTimeout(temporizador);
    caixa.remove();
  };
  if (acao) {
    const botao = el("button", { type: "button", class: "aviso-acao", texto: acao.texto });
    botao.addEventListener("click", async () => {
      botao.disabled = true;
      try {
        await acao.executar();
      } finally {
        fechar();
      }
    });
    caixa.append(botao);
  }
  const fecharBotao = el("button", { type: "button", class: "aviso-fechar", "aria-label": "Fechar aviso" }, icone("fechar", "ic-sm"));
  fecharBotao.addEventListener("click", fechar);
  caixa.append(fecharBotao);
  obterRegiao().replaceChildren(caixa);
  const agendar = () => (temporizador = setTimeout(fechar, duracao));
  caixa.addEventListener("pointerenter", () => clearTimeout(temporizador));
  caixa.addEventListener("pointerleave", agendar);
  caixa.addEventListener("focusin", () => clearTimeout(temporizador));
  agendar();
  return fechar;
}
