import { el } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { sairDaConta } from "../app.js";

export async function montar(raiz) {
  const usuario = usuarioAtual();
  raiz.append(
    el("h1", { texto: `Olá, ${usuario.nome}` }),
    el("p", { class: "suave", texto: "O painel chega no próximo bloco." }),
    el("button", { class: "btn btn-secundario", type: "button", onclick: sairDaConta, texto: "Sair" }),
  );
}
