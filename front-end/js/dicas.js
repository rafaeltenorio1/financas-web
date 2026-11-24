import { api } from "./api.js";
import { el, icone } from "./dom.js";
import { logo } from "./logo.js";
import { definirUsuario, usuarioAtual } from "./sessao.js";

export function dicaVista(id) {
  const usuario = usuarioAtual();
  return !usuario || (usuario.dicas_vistas ?? []).includes(id);
}

export function marcarDica(id) {
  const usuario = usuarioAtual();
  if (!usuario || dicaVista(id)) return;
  definirUsuario({ ...usuario, dicas_vistas: [...(usuario.dicas_vistas ?? []), id] });
  api.post("/auth/me/dicas", { id }).catch(() => {});
}

const PONTOS = [
  { ic: "transacoes", texto: "Anote seus gastos e ganhos em poucos toques, ou importe o extrato do banco." },
  { ic: "contas", texto: "Cadastre as contas do mês e receba um aviso por e-mail antes de vencer." },
  { ic: "painel", texto: "Veja no painel para onde o dinheiro está indo." },
];

export function mostrarBoasVindas() {
  if (dicaVista("boas-vindas") || document.querySelector(".boas-vindas")) return Promise.resolve();
  return new Promise((resolver) => {
    const comecar = el("button", { type: "button", class: "btn btn-primario bv-botao", texto: "Começar" });
    const dialogo = el(
      "dialog",
      { class: "boas-vindas", "aria-labelledby": "bv-titulo", "aria-describedby": "bv-texto" },
      el(
        "div",
        { class: "bv-caixa" },
        logo({ classe: "bv-logo" }),
        el("h2", { id: "bv-titulo", texto: "Boas-vindas à Balancia" }),
        el("p", { id: "bv-texto", class: "bv-texto", texto: "Seu dinheiro organizado, sem planilha." }),
        el(
          "ul",
          { class: "bv-pontos" },
          ...PONTOS.map((p) => el("li", {}, el("span", { class: "bv-ic", "aria-hidden": "true" }, icone(p.ic, "ic-sm")), el("span", { texto: p.texto }))),
        ),
        comecar,
      ),
    );
    comecar.addEventListener("click", () => dialogo.close());
    dialogo.addEventListener("close", () => {
      marcarDica("boas-vindas");
      dialogo.remove();
      resolver();
    });
    document.body.append(dialogo);
    dialogo.showModal();
    comecar.focus();
  });
}

export function dicaUnica(id, texto) {
  if (dicaVista(id)) return null;
  const fechar = el("button", { type: "button", class: "dica-unica-fechar", "aria-label": "Fechar dica" }, icone("fechar", "ic-sm"));
  const caixa = el("div", { class: "dica-unica", role: "note" }, icone("info", "ic-sm"), el("span", { texto }), fechar);
  fechar.addEventListener("click", () => {
    marcarDica(id);
    caixa.remove();
  });
  return caixa;
}
