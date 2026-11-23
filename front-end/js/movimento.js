import { moeda } from "./formatos.js";

const CHAVE = "animacoes";
const SUAVE = "cubic-bezier(0.2, 0, 0, 1)";

export function animacoesLigadas() {
  try {
    return localStorage.getItem(CHAVE) !== "desligadas";
  } catch {
    return true;
  }
}

export function aplicarPreferenciaDeAnimacoes() {
  document.documentElement.classList.toggle("sem-animacoes", !animacoesLigadas());
}

export function definirAnimacoes(ligadas) {
  try {
    if (ligadas) localStorage.removeItem(CHAVE);
    else localStorage.setItem(CHAVE, "desligadas");
  } catch {}
  aplicarPreferenciaDeAnimacoes();
}

export function animarNumeros(raiz, duracao = 750) {
  if (!animacoesLigadas()) return;
  for (const alvo of raiz.querySelectorAll("[data-valor]")) {
    const final = Number(alvo.dataset.valor);
    if (!Number.isFinite(final) || final === 0) continue;
    const textoFinal = alvo.textContent;
    if (textoFinal !== moeda(final)) continue;
    alvo.setAttribute("aria-label", textoFinal);
    const inicio = performance.now();
    const passo = (agora) => {
      if (!alvo.isConnected) return;
      const t = Math.min(1, (agora - inicio) / duracao);
      const suavizado = 1 - (1 - t) ** 3;
      alvo.textContent = t < 1 ? moeda(final * suavizado) : textoFinal;
      if (t < 1) requestAnimationFrame(passo);
      else alvo.removeAttribute("aria-label");
    };
    alvo.textContent = moeda(0);
    requestAnimationFrame(passo);
  }
}

export function destacar(elemento) {
  if (!elemento || !animacoesLigadas()) return;
  elemento.classList.remove("destaque-novo");
  void elemento.offsetWidth;
  elemento.classList.add("destaque-novo");
  elemento.addEventListener("animationend", () => elemento.classList.remove("destaque-novo"), { once: true });
  elemento.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

export async function recolher(elemento) {
  if (!elemento || !animacoesLigadas()) return;
  const altura = elemento.getBoundingClientRect().height;
  const estilo = getComputedStyle(elemento);
  elemento.style.overflow = "hidden";
  const animacao = elemento.animate(
    [
      { height: `${altura}px`, opacity: 1, paddingTop: estilo.paddingTop, paddingBottom: estilo.paddingBottom },
      { height: `${altura}px`, opacity: 0, offset: 0.4, paddingTop: estilo.paddingTop, paddingBottom: estilo.paddingBottom },
      { height: "0px", opacity: 0, paddingTop: "0px", paddingBottom: "0px" },
    ],
    { duration: 320, easing: SUAVE, fill: "forwards" },
  );
  await animacao.finished.catch(() => {});
}

export function tremer(elemento) {
  if (!elemento || !animacoesLigadas()) return;
  elemento.animate(
    [{ transform: "translateX(0)" }, { transform: "translateX(-6px)" }, { transform: "translateX(5px)" }, { transform: "translateX(-3px)" }, { transform: "translateX(2px)" }, { transform: "translateX(0)" }],
    { duration: 360, easing: "ease-out" },
  );
}

export function entrarDoLado(elemento, direcao) {
  if (!elemento || !direcao || !animacoesLigadas()) return;
  elemento.animate([{ transform: `translateX(${direcao * 28}px)`, opacity: 0 }, { transform: "none", opacity: 1 }], { duration: 280, easing: SUAVE });
}
