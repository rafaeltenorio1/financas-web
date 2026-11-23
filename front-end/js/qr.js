const SVG = "http://www.w3.org/2000/svg";
const ARQUIVO = "js/vendor/qrcode-generator-1.4.4.js";
const MARGEM = 2;

let carregando = null;

function carregarBiblioteca() {
  if (window.qrcode) return Promise.resolve(window.qrcode);
  carregando ??= new Promise((resolver, rejeitar) => {
    const script = document.createElement("script");
    script.src = ARQUIVO;
    script.addEventListener("load", () => (window.qrcode ? resolver(window.qrcode) : rejeitar(new Error("QR indisponível"))));
    script.addEventListener("error", () => {
      carregando = null;
      rejeitar(new Error("QR indisponível"));
    });
    document.head.append(script);
  });
  return carregando;
}

export async function desenharQr(texto, rotulo) {
  const qrcode = await carregarBiblioteca();
  const qr = qrcode(0, "M");
  qr.addData(texto, "Byte");
  qr.make();
  const tamanho = qr.getModuleCount();
  const total = tamanho + MARGEM * 2;
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${total} ${total}`);
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", rotulo);
  svg.setAttribute("shape-rendering", "crispEdges");
  const fundo = document.createElementNS(SVG, "rect");
  fundo.setAttribute("width", String(total));
  fundo.setAttribute("height", String(total));
  fundo.setAttribute("fill", "#ffffff");
  svg.append(fundo);
  const partes = [];
  for (let linha = 0; linha < tamanho; linha += 1) {
    for (let coluna = 0; coluna < tamanho; coluna += 1) {
      if (qr.isDark(linha, coluna)) partes.push(`M${coluna + MARGEM} ${linha + MARGEM}h1v1h-1z`);
    }
  }
  const caminho = document.createElementNS(SVG, "path");
  caminho.setAttribute("d", partes.join(""));
  caminho.setAttribute("fill", "#051f20");
  svg.append(caminho);
  return svg;
}
