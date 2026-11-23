const SVG = "http://www.w3.org/2000/svg";

function elementoSvg(tag, atributos) {
  const elemento = document.createElementNS(SVG, tag);
  for (const [nome, valor] of Object.entries(atributos)) elemento.setAttribute(nome, String(valor));
  return elemento;
}

export function logo({ animada = false, classe = "" } = {}) {
  const svg = elementoSvg("svg", { viewBox: "0 0 32 32", "aria-hidden": "true", focusable: "false", class: `logo${animada ? " logo-animada" : ""} ${classe}`.trim() });
  svg.append(elementoSvg("rect", { class: "logo-fundo", width: 32, height: 32, rx: 10 }));
  if (animada) svg.append(elementoSvg("rect", { class: "logo-contorno", x: 1.1, y: 1.1, width: 29.8, height: 29.8, rx: 9, pathLength: 100 }));
  svg.append(elementoSvg("path", { class: "logo-linha", d: "M8 21l5-5 4 3 7-8", pathLength: 100 }));
  return svg;
}
