import { carregarUsuario, usuarioAtual } from "./sessao.js";

const rotas = new Map();
let desmontarAtual = null;
let montarLayout = null;
let raizApp = null;
let versao = 0;
let guardaDeSaida = null;
let hashAtual = null;
let ignorarProxima = false;

export function definirGuardaDeSaida(funcao) {
  guardaDeSaida = funcao;
}

export function registrar(caminho, definicao) {
  rotas.set(caminho, { publica: false, soDeslogado: false, ...definicao });
}

export function navegar(caminho, { substituir = false, forcar = false } = {}) {
  if (forcar) guardaDeSaida = null;
  const destino = `#${caminho}`;
  if (location.hash === destino) {
    renderizar();
    return;
  }
  if (substituir) {
    history.replaceState(null, "", destino);
    renderizar();
  } else {
    location.hash = destino;
  }
}

function rotaAtual() {
  const bruto = location.hash.replace(/^#/, "") || "/";
  const [caminho, consulta = ""] = bruto.split("?");
  return { caminho: caminho || "/", parametros: new URLSearchParams(consulta) };
}

async function renderizar() {
  if (ignorarProxima) {
    ignorarProxima = false;
    return;
  }
  if (guardaDeSaida && hashAtual !== null && location.hash !== hashAtual) {
    const resposta = guardaDeSaida();
    if (resposta !== true) {
      const destino = location.hash;
      ignorarProxima = true;
      location.hash = hashAtual;
      if (!(await resposta)) return;
      guardaDeSaida = null;
      location.hash = destino;
      return;
    }
  }
  guardaDeSaida = null;
  hashAtual = location.hash;
  const minhaVersao = ++versao;
  const { caminho, parametros } = rotaAtual();
  const rota = rotas.get(caminho);
  if (!rota) {
    navegar("/", { substituir: true });
    return;
  }

  const usuario = rota.publica && !rota.soDeslogado ? usuarioAtual() : await carregarUsuario();
  if (minhaVersao !== versao) return;

  if (!rota.publica && !usuario) {
    const volta = encodeURIComponent(caminho + (parametros.size ? `?${parametros}` : ""));
    navegar(`/entrar${caminho === "/" ? "" : `?volta=${volta}`}`, { substituir: true });
    return;
  }
  if (rota.soDeslogado && usuario) {
    navegar("/", { substituir: true });
    return;
  }

  if (typeof desmontarAtual === "function") desmontarAtual();
  desmontarAtual = null;

  const modulo = await rota.carregar();
  if (minhaVersao !== versao) return;

  const alvo = montarLayout(raizApp, { caminho, logado: !rota.publica });
  document.title = rota.titulo ? `${rota.titulo} | Balancia` : "Balancia";
  desmontarAtual = await modulo.montar(alvo, { parametros, navegar });
  const foco = alvo.querySelector("[data-foco-inicial]") || alvo.querySelector("h1");
  if (foco) {
    if (!foco.hasAttribute("tabindex") && !foco.matches("input, button, select, textarea, a")) foco.setAttribute("tabindex", "-1");
    foco.focus({ preventScroll: true });
  }
}

export function iniciarRotas(raiz, layout) {
  raizApp = raiz;
  montarLayout = layout;
  window.addEventListener("hashchange", renderizar);
  return renderizar();
}

export function recarregar() {
  hashAtual = null;
  renderizar();
}

export function caminhoAtual() {
  return rotaAtual().caminho;
}
