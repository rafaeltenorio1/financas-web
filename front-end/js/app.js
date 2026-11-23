import { el, icone } from "./dom.js";
import { registrar, iniciarRotas, navegar, caminhoAtual, recarregar } from "./rotas.js";
import { usuarioAtual, encerrarLocalmente, sair } from "./sessao.js";

const ITENS_NAV = [
  { caminho: "/", rotulo: "Painel", icone: "painel" },
  { caminho: "/transacoes", rotulo: "Transações", icone: "transacoes" },
  { caminho: "/nova", rotulo: "Nova transação", icone: "mais", novo: true },
  { caminho: "/contas", rotulo: "Contas", icone: "contas" },
  { caminho: "/categorias", rotulo: "Categorias", icone: "categorias", soLateral: true },
  { caminho: "/conta", rotulo: "Conta", icone: "conta" },
];

registrar("/entrar", { publica: true, soDeslogado: true, titulo: "Entrar", carregar: () => import("./telas/login.js") });
registrar("/", { titulo: "Painel", carregar: () => import("./telas/painel.js") });

const emBreve = () => import("./telas/em-breve.js");
registrar("/cadastro", { publica: true, soDeslogado: true, titulo: "Criar conta", carregar: () => import("./telas/cadastro.js") });
registrar("/esqueci-senha", { publica: true, soDeslogado: true, titulo: "Esqueci a senha", carregar: () => import("./telas/esqueci-senha.js") });
registrar("/redefinir-senha", { publica: true, titulo: "Criar senha nova", carregar: () => import("./telas/redefinir-senha.js") });
registrar("/verificar-email", { publica: true, titulo: "Confirmar e-mail", carregar: () => import("./telas/verificar-email.js") });
registrar("/confirmar-email", { publica: true, titulo: "Confirmar e-mail novo", carregar: () => import("./telas/confirmar-email.js") });
registrar("/nova", { titulo: "Nova transação", carregar: () => import("./telas/nova.js") });
registrar("/transacoes", { titulo: "Transações", carregar: () => import("./telas/transacoes.js") });
registrar("/contas", { titulo: "Contas", carregar: () => import("./telas/contas.js") });
registrar("/categorias", { titulo: "Categorias", carregar: () => import("./telas/categorias.js") });
registrar("/importar", { titulo: "Importar extrato", carregar: () => import("./telas/importar.js") });
registrar("/conta", { titulo: "Em construção", carregar: emBreve });

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
    const link = el(
      "a",
      { class: `nav-item${item.novo ? " nav-novo" : ""}${item.novo && caminho === "/transacoes" ? " nav-novo-na-tela" : ""}${item.soLateral ? " nav-lateral" : ""}`, href: `#${item.caminho}`, "aria-current": atual ? "page" : null },
      icone(item.icone),
      el("span", { texto: item.rotulo }),
    );
    if (item.novo) {
      link.setAttribute("aria-haspopup", "dialog");
      link.addEventListener("click", async (evento) => {
        if (evento.ctrlKey || evento.metaKey || evento.shiftKey || evento.button !== 0) return;
        evento.preventDefault();
        const { abrirFormularioTransacao } = await import("./transacao-form.js");
        abrirFormularioTransacao({ aoSalvar: () => recarregar() });
      });
    }
    nav.append(link);
  }
  const sair = el("button", { type: "button", class: "nav-item nav-sair" }, icone("sair"), el("span", { texto: "Sair" }));
  sair.addEventListener("click", sairDaConta);
  nav.append(sair);
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
  navegar(`/entrar?volta=${volta}`, { substituir: true, forcar: true });
});

export async function sairDaConta() {
  try {
    await sair();
  } finally {
    navegar("/entrar", { substituir: true });
  }
}

iniciarRotas(document.getElementById("app"), layout);
