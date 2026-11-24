const CHAVE_DICA = "dica-instalar";
const ouvintes = new Set();
let pedidoDeInstalacao = null;

const ehIos = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const ehCelular = ehIos || /android/i.test(navigator.userAgent);

function avisarOuvintes() {
  for (const ouvinte of ouvintes) ouvinte(estadoDaInstalacao());
}

export function appInstalado() {
  return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
}

export function estadoDaInstalacao() {
  if (appInstalado()) return "instalado";
  if (pedidoDeInstalacao) return "disponivel";
  if (ehIos) return "ios";
  return "indisponivel";
}

export function aoMudarInstalacao(ouvinte) {
  ouvintes.add(ouvinte);
  return () => ouvintes.delete(ouvinte);
}

export async function instalar() {
  if (!pedidoDeInstalacao) return false;
  const pedido = pedidoDeInstalacao;
  pedidoDeInstalacao = null;
  await pedido.prompt();
  const { outcome } = await pedido.userChoice;
  avisarOuvintes();
  return outcome === "accepted";
}

export function deveSugerirInstalacao() {
  if (!ehCelular || appInstalado()) return false;
  try {
    return !localStorage.getItem(CHAVE_DICA);
  } catch {
    return false;
  }
}

export function marcarSugestaoVista() {
  try {
    localStorage.setItem(CHAVE_DICA, "1");
  } catch {}
}

export function iniciarInstalacao() {
  window.addEventListener("beforeinstallprompt", (evento) => {
    evento.preventDefault();
    pedidoDeInstalacao = evento;
    avisarOuvintes();
  });
  window.addEventListener("appinstalled", () => {
    pedidoDeInstalacao = null;
    marcarSugestaoVista();
    avisarOuvintes();
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
    });
  }
}
