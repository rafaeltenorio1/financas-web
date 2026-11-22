import { el, icone } from "./dom.js";
import { registrar, iniciarRotas, navegar, caminhoAtual } from "./rotas.js";
import { usuarioAtual, encerrarLocalmente, sair } from "./sessao.js";

const ITENS_NAV = [
  { caminho: "/", rotulo: "Painel", icone: "painel" },
  { caminho: "/transacoes", rotulo: "Transações", icone: "transacoes" },
  { caminho: "/nova", rotulo: "Nova transação", icone: "mais", novo: true },
  { caminho: "/contas", rotulo: "Contas", icone: "contas" },
  { caminho: "/conta", rotulo: "Conta", icone: "conta" },
];

registrar("/entrar", { publica: true, soDeslogado: true, titulo: "Entrar", carregar: () => import("./telas/login.js") });
registrar("/", { titulo: "Painel", carregar: () => import("./telas/painel.js") });

const emBreve = () => import("./telas/em-breve.js");
for (const caminho of ["/cadastro", "/esqueci-senha"]) registrar(caminho, { publica: true, titulo: "Em construção", carregar: emBreve });
for (const caminho of ["/transacoes", "/nova", "/contas", "/conta"]) registrar(caminho, { titulo: "Em construção", carregar: emBreve });

let mensagemPendente = null;

export function mensagemParaProximaTela() {
  const m = mensagemPendente;
  mensagemPendente = null;
  return m;
}

function navegacao(caminho) {
  const nav = el("nav", { class: "nav", "aria-label": "Principal" }, el("a", { class: "nav-marca", href: "#/", texto: "Finanças", translate: "no" }));
  for (const item of ITENS_NAV) {
    const atual = item.caminho === caminho;
    nav.append(
      el(
        "a",
        { class: `nav-item${item.novo ? " nav-novo" : ""}`, href: `#${item.caminho}`, "aria-current": atual ? "page" : null },
        icone(item.icone),
        el("span", { texto: item.rotulo }),
      ),
    );
  }
  return nav;
}

function layout(raiz, { caminho, logado }) {
  raiz.replaceChildren();
  if (!logado) {
    const principal = el("main", { id: "conteudo" });
    raiz.append(principal);
    return principal;
  }
  const principal = el("main", { class: "conteudo", id: "conteudo", tabindex: "-1" });
  const pular = el("a", { class: "pular", href: "#conteudo", texto: "Pular para o conteúdo" });
  pular.addEventListener("click", (evento) => {
    evento.preventDefault();
    principal.focus();
  });
  raiz.append(pular, el("div", { class: "app" }, navegacao(caminho), principal));
  return principal;
}

window.addEventListener("sessao-expirada", () => {
  const estavaLogado = usuarioAtual() !== null;
  encerrarLocalmente();
  if (!estavaLogado || caminhoAtual() === "/entrar") return;
  mensagemPendente = { tipo: "aviso", texto: "Sua sessão expirou. Entre novamente para continuar." };
  const volta = encodeURIComponent(caminhoAtual());
  navegar(`/entrar?volta=${volta}`, { substituir: true });
});

export async function sairDaConta() {
  try {
    await sair();
  } finally {
    navegar("/entrar", { substituir: true });
  }
}

iniciarRotas(document.getElementById("app"), layout);
