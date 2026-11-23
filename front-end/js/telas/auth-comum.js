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

export const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validarEmail(c) {
  const valor = c.entrada.value.trim();
  marcarErro(c, !valor ? "Informe seu e-mail." : !EMAIL_VALIDO.test(valor) ? "Confira o e-mail: falta algo como @ ou o domínio." : "");
  return !c.entrada.hasAttribute("aria-invalid");
}

export function validarSenhaNova(c) {
  const valor = c.entrada.value;
  marcarErro(c, !valor ? "Crie uma senha." : valor.length < 8 ? "A senha precisa ter pelo menos 8 caracteres." : valor.length > 128 ? "A senha pode ter no máximo 128 caracteres." : "");
  return !c.entrada.hasAttribute("aria-invalid");
}

const NIVEIS = ["", "Senha fraca: use mais caracteres ou misture letras, números e símbolos.", "Senha razoável.", "Senha forte."];

export function medidorDeForca(entrada) {
  const texto = el("p", { class: "forca-texto", "aria-live": "polite", texto: "Use pelo menos 8 caracteres." });
  const bloco = el("div", { class: "forca", "data-nivel": "0" }, el("div", { class: "forca-barras", "aria-hidden": "true" }, el("span"), el("span"), el("span")), texto);
  entrada.addEventListener("input", () => {
    const v = entrada.value;
    let pontos = 0;
    if (v.length >= 8) pontos += 1;
    if (v.length >= 12) pontos += 1;
    if (/[a-z]/.test(v) && /[A-Z]/.test(v)) pontos += 1;
    if (/\d/.test(v)) pontos += 1;
    if (/[^A-Za-z0-9]/.test(v)) pontos += 1;
    const nivel = !v ? 0 : v.length < 8 ? 1 : pontos >= 4 ? 3 : pontos >= 2 ? 2 : 1;
    bloco.dataset.nivel = String(nivel);
    texto.textContent = nivel ? NIVEIS[nivel] : "Use pelo menos 8 caracteres.";
  });
  return bloco;
}

export function lerTokenDaUrl(parametros, caminho) {
  const token = parametros.get("token");
  if (token) history.replaceState(null, "", `#${caminho}`);
  return token;
}

export function cartaoDeResultado({ simbolo, titulo, texto, destaque, acoes = [], aviso }) {
  const cartao = el("section", { class: "auth-cartao", "aria-labelledby": "titulo-resultado" }, selo(simbolo));
  cartao.append(el("h1", { class: "auth-titulo", id: "titulo-resultado", texto: titulo, tabindex: "-1", "data-foco-inicial": true }));
  const p = el("p", { class: "auth-sub", texto });
  if (destaque) p.append(" ", el("span", { class: "auth-destaque", texto: destaque }));
  cartao.append(p);
  if (aviso) cartao.append(aviso);
  if (acoes.length) cartao.append(el("div", { class: "auth-acoes" }, ...acoes));
  return cartao;
}
