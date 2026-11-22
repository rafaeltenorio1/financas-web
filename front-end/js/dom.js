const SVG = "http://www.w3.org/2000/svg";

export function el(tag, atributos = {}, ...filhos) {
  const elemento = document.createElement(tag);
  for (const [nome, valor] of Object.entries(atributos)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (nome === "class") elemento.className = valor;
    else if (nome === "texto") elemento.textContent = valor;
    else if (nome.startsWith("on") && typeof valor === "function") elemento.addEventListener(nome.slice(2), valor);
    else if (valor === true) elemento.setAttribute(nome, "");
    else elemento.setAttribute(nome, valor);
  }
  elemento.append(...filhos.flat().filter((f) => f !== null && f !== undefined && f !== false));
  return elemento;
}

export function icone(id, classe = "ic") {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", classe);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const uso = document.createElementNS(SVG, "use");
  uso.setAttribute("href", `img/icones.svg#${id}`);
  svg.append(uso);
  return svg;
}

export function mensagem(alvo, tipo, texto) {
  alvo.className = `mensagem mensagem-${tipo}`;
  alvo.replaceChildren();
  if (!texto) return;
  const icones = { erro: "erro", aviso: "alerta", sucesso: "sucesso", info: "info" };
  alvo.append(icone(icones[tipo] || "info", "ic-sm"), el("span", { texto }));
}

const originais = new WeakMap();

export function ocupado(botao, sim, textoOcupado) {
  if (sim) {
    if (!originais.has(botao)) originais.set(botao, [...botao.childNodes]);
    botao.setAttribute("aria-busy", "true");
    botao.disabled = true;
    botao.replaceChildren(el("span", { class: "girando", "aria-hidden": "true" }), textoOcupado || botao.textContent);
  } else {
    botao.removeAttribute("aria-busy");
    botao.disabled = false;
    if (originais.has(botao)) botao.replaceChildren(...originais.get(botao));
    originais.delete(botao);
  }
}
