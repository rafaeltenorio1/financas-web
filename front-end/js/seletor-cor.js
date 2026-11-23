import { el } from "./dom.js";

const CHAVE_RECENTES = "cores-recentes";
const MAXIMO_RECENTES = 8;
const SUGESTOES = ["#5fa8f5", "#f57b6b", "#b98cf0", "#4fd1a5", "#f2c14e", "#ff8fc7", "#9fd36b", "#c9a27a"];
const HEX = /^#[0-9a-f]{6}$/;

export function hexParaHsv(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const d = max - Math.min(r, g, b);
  let h = 0;
  if (d) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h = (h * 60 + 360) % 360;
  }
  return { h, s: max ? d / max : 0, v: max };
}

export function hsvParaHex({ h, s, v }) {
  const f = (n) => {
    const k = (n + h / 60) % 6;
    return Math.round((v - v * s * Math.max(0, Math.min(k, 4 - k, 1))) * 255);
  };
  return `#${[f(5), f(3), f(1)].map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

function lerRecentes() {
  try {
    const lista = JSON.parse(localStorage.getItem(CHAVE_RECENTES) || "[]");
    return Array.isArray(lista) ? lista.filter((c) => HEX.test(c)) : [];
  } catch {
    return [];
  }
}

export function guardarCorRecente(hex) {
  if (!HEX.test(hex)) return;
  try {
    const lista = [hex, ...lerRecentes().filter((c) => c !== hex)].slice(0, MAXIMO_RECENTES);
    localStorage.setItem(CHAVE_RECENTES, JSON.stringify(lista));
  } catch {}
}

export function criarSeletorDeCor({ id, inicial, coresDasCategorias = [], aoMudar, aoFechar }) {
  let hsv = hexParaHsv(inicial);
  const recentes = [...new Set([...lerRecentes(), ...coresDasCategorias.filter((c) => HEX.test(c))])].slice(0, MAXIMO_RECENTES);

  const area = el("div", { class: "sc-area", role: "slider", tabindex: "0", "aria-label": "Tom e brilho", "aria-valuemin": "0", "aria-valuemax": "100" });
  const alvo = el("span", { class: "sc-alvo", "aria-hidden": "true" });
  area.append(alvo);
  const matiz = el("input", { type: "range", class: "sc-matiz", min: "0", max: "359", step: "1", "aria-label": "Matiz" });
  const amostra = el("span", { class: "sc-amostra", "aria-hidden": "true" });
  const codigo = el("input", { class: "entrada sc-codigo", id: `${id}-codigo`, name: "codigo-cor", autocomplete: "off", spellcheck: "false", maxlength: 7, "aria-describedby": `${id}-codigo-erro` });
  const erroCodigo = el("p", { class: "campo-erro", id: `${id}-codigo-erro` });
  const pronto = el("button", { type: "button", class: "btn btn-primario sc-pronto", texto: "Pronto" });

  const linhaDeCores = (titulo, cores) => {
    if (!cores.length) return null;
    const grupo = el("div", { class: "sc-linha", role: "group", "aria-label": titulo });
    for (const cor of cores) {
      const botao = el("button", { type: "button", class: "sc-recente", title: cor, "aria-label": cor });
      botao.style.setProperty("--amostra", cor);
      botao.addEventListener("click", () => definir(hexParaHsv(cor), true));
      grupo.append(botao);
    }
    return el("div", {}, el("p", { class: "sc-titulo", texto: titulo }), grupo);
  };

  const painel = el(
    "div",
    { class: "sc-painel", id, role: "dialog", "aria-label": "Escolher outra cor" },
    area,
    el("div", { class: "sc-barra" }, amostra, matiz),
    el("div", { class: "sc-codigo-linha" }, el("label", { for: `${id}-codigo`, texto: "Código" }), codigo, pronto),
    erroCodigo,
    linhaDeCores(recentes.length ? "Recentes" : "Sugestões", [...recentes, ...SUGESTOES.filter((c) => !recentes.includes(c))].slice(0, MAXIMO_RECENTES)),
  );

  function desenhar(atualizarCodigo = true) {
    const hex = hsvParaHex(hsv);
    area.style.setProperty("--matiz", `hsl(${hsv.h} 100% 50%)`);
    alvo.style.left = `${hsv.s * 100}%`;
    alvo.style.top = `${(1 - hsv.v) * 100}%`;
    alvo.style.background = hex;
    amostra.style.background = hex;
    matiz.value = String(Math.round(hsv.h));
    area.setAttribute("aria-valuenow", String(Math.round(hsv.s * 100)));
    area.setAttribute("aria-valuetext", `saturação ${Math.round(hsv.s * 100)}%, brilho ${Math.round(hsv.v * 100)}%`);
    if (atualizarCodigo) {
      codigo.value = hex;
      erroCodigo.textContent = "";
      codigo.removeAttribute("aria-invalid");
    }
    return hex;
  }

  function definir(novo, atualizarCodigo = true) {
    hsv = { h: Math.min(359, Math.max(0, novo.h)), s: Math.min(1, Math.max(0, novo.s)), v: Math.min(1, Math.max(0, novo.v)) };
    aoMudar?.(desenhar(atualizarCodigo));
  }

  function pelaPosicao(evento) {
    const r = area.getBoundingClientRect();
    definir({ h: hsv.h, s: (evento.clientX - r.left) / r.width, v: 1 - (evento.clientY - r.top) / r.height });
  }

  area.addEventListener("pointerdown", (evento) => {
    evento.preventDefault();
    area.focus();
    area.setPointerCapture(evento.pointerId);
    pelaPosicao(evento);
    const mover = (e) => pelaPosicao(e);
    const soltar = () => {
      area.removeEventListener("pointermove", mover);
      area.removeEventListener("pointerup", soltar);
      area.removeEventListener("pointercancel", soltar);
    };
    area.addEventListener("pointermove", mover);
    area.addEventListener("pointerup", soltar);
    area.addEventListener("pointercancel", soltar);
  });
  area.addEventListener("keydown", (evento) => {
    const passo = evento.shiftKey ? 0.1 : 0.02;
    const mudancas = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, passo], ArrowDown: [0, -passo] };
    const mudanca = mudancas[evento.key];
    if (!mudanca) return;
    evento.preventDefault();
    definir({ h: hsv.h, s: hsv.s + mudanca[0], v: hsv.v + mudanca[1] });
  });
  matiz.addEventListener("input", () => definir({ ...hsv, h: Number(matiz.value) }));
  codigo.addEventListener("input", () => {
    let texto = codigo.value.trim().toLowerCase();
    if (texto && !texto.startsWith("#")) texto = `#${texto}`;
    if (HEX.test(texto)) definir(hexParaHsv(texto), false);
  });
  codigo.addEventListener("change", () => {
    let texto = codigo.value.trim().toLowerCase();
    if (texto && !texto.startsWith("#")) texto = `#${texto}`;
    if (HEX.test(texto)) {
      codigo.value = texto;
      erroCodigo.textContent = "";
      codigo.removeAttribute("aria-invalid");
    } else {
      erroCodigo.textContent = "Use o formato #1a2b3c.";
      codigo.setAttribute("aria-invalid", "true");
    }
  });
  painel.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
      evento.preventDefault();
      evento.stopPropagation();
      aoFechar?.();
    }
  });
  pronto.addEventListener("click", () => aoFechar?.());

  desenhar();
  return {
    painel,
    focar: () => area.focus({ preventScroll: true }),
    definirCor(hex) {
      if (HEX.test(hex)) {
        hsv = hexParaHsv(hex);
        desenhar();
      }
    },
  };
}
