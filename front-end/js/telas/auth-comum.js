import { el, icone } from "../dom.js";

const SVG = "http://www.w3.org/2000/svg";

function sinalDaMarca() {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 32 32");
  svg.setAttribute("aria-hidden", "true");
  const fundo = document.createElementNS(SVG, "rect");
  for (const [k, v] of Object.entries({ width: 32, height: 32, rx: 10, fill: "var(--destaque)" })) fundo.setAttribute(k, v);
  const linha = document.createElementNS(SVG, "path");
  for (const [k, v] of Object.entries({ d: "M8 21l5-5 4 3 7-8", fill: "none", stroke: "var(--fundo)", "stroke-width": 2.6, "stroke-linecap": "round", "stroke-linejoin": "round" })) linha.setAttribute(k, v);
  svg.append(fundo, linha);
  return svg;
}

export function telaAuth(...conteudo) {
  return el(
    "div",
    { class: "auth" },
    el("div", { class: "auth-caixa" }, el("a", { class: "auth-marca", href: "#/entrar" }, sinalDaMarca(), el("span", { texto: "Finanças", translate: "no" })), ...conteudo),
  );
}

export function selo(idIcone) {
  return el("div", { class: "selo-anel", "aria-hidden": "true" }, el("span", {}, icone(idIcone)));
}

export function campo({ id, rotulo, ajuda, acessorio, ...atributos }) {
  const entrada = el("input", { class: "entrada", id, name: id, ...atributos });
  const erro = el("p", { class: "campo-erro", id: `${id}-erro` });
  const descritores = [`${id}-erro`];
  const partes = [];
  const rotuloEl = el("label", { for: id, texto: rotulo });
  partes.push(acessorio ? el("div", { class: "campo-linha" }, rotuloEl, acessorio) : rotuloEl);
  partes.push(entrada);
  if (ajuda) {
    partes.push(el("p", { class: "campo-ajuda", id: `${id}-ajuda`, texto: ajuda }));
    descritores.unshift(`${id}-ajuda`);
  }
  partes.push(erro);
  entrada.setAttribute("aria-describedby", descritores.join(" "));
  return { bloco: el("div", { class: "campo" }, ...partes), entrada, erro };
}

export function campoSenha(opcoes) {
  const resultado = campo({ ...opcoes, type: "password" });
  const botao = el(
    "button",
    { type: "button", class: "btn btn-icone", "aria-label": "Mostrar senha", "aria-pressed": "false", "aria-controls": opcoes.id },
    icone("olho", "ic-sm"),
  );
  botao.addEventListener("click", () => {
    const mostrar = resultado.entrada.type === "password";
    resultado.entrada.type = mostrar ? "text" : "password";
    botao.setAttribute("aria-pressed", String(mostrar));
    botao.replaceChildren(icone(mostrar ? "olho-fechado" : "olho", "ic-sm"));
    resultado.entrada.focus();
  });
  const envoltorio = el("div", { class: "entrada-com-botao" });
  resultado.entrada.before(envoltorio);
  envoltorio.append(resultado.entrada, botao);
  return { ...resultado, botaoVer: botao };
}

export function marcarErro(c, texto) {
  c.erro.textContent = texto || "";
  if (texto) c.entrada.setAttribute("aria-invalid", "true");
  else c.entrada.removeAttribute("aria-invalid");
}

export function destinoSeguro(volta) {
  if (!volta || !volta.startsWith("/") || volta.startsWith("//") || volta.startsWith("/entrar")) return "/";
  return volta;
}
