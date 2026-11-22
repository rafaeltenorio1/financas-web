import { el } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { telaAuth } from "./auth-comum.js";

export async function montar(raiz) {
  const logado = usuarioAtual() !== null;
  const conteudo = [
    el("h1", { class: "auth-titulo", texto: "Esta tela ainda está em construção" }),
    el("p", { class: "auth-sub", texto: "Ela chega nas próximas etapas do projeto." }),
    el("p", { class: "auth-rodape" }, el("a", { href: logado ? "#/" : "#/entrar", texto: logado ? "Voltar ao painel" : "Voltar para o login" })),
  ];
  raiz.append(logado ? el("div", {}, ...conteudo) : telaAuth(el("section", { class: "auth-cartao" }, ...conteudo)));
}
