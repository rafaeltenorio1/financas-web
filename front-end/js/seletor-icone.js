import { el, icone } from "./dom.js";
import { ICONES, iconeValido } from "./categorias.js";
import { listaDeMarcas, marcaPorId } from "./marcas.js";
import { caixaDaMarca, caixaDoSimbolo } from "./painel/componentes.js";

const normalizar = (texto) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
const MARCAS_SEM_BUSCA = 40;

export function codigoValido(codigo) {
  if (typeof codigo !== "string") return false;
  if (codigo.startsWith("m-")) return marcaPorId(codigo.slice(2)) !== null;
  return iconeValido(codigo);
}

export function nomeDoCodigo(codigo) {
  if (codigo?.startsWith("m-")) return marcaPorId(codigo.slice(2))?.nome ?? null;
  return ICONES.find(([id]) => id === codigo)?.[1] ?? null;
}

export function criarSeletorDeIcone({ prefixo, inicial = null, categoriaAtual, aoMudar }) {
  const estado = { codigo: codigoValido(inicial) ? inicial : null, aba: inicial?.startsWith("c-") ? "icones" : "marcas", busca: "" };
  const marcas = listaDeMarcas().sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

  const abas = [
    ["marcas", "Marcas"],
    ["icones", "Ícones"],
  ].map(([aba, rotulo]) => {
    const botao = el("button", { type: "button", "aria-pressed": String(estado.aba === aba), texto: rotulo });
    botao.addEventListener("click", () => {
      estado.aba = aba;
      abas.forEach((b) => b.setAttribute("aria-pressed", String(b === botao)));
      desenhar();
      if (aba === "marcas") busca.focus();
    });
    return botao;
  });
  const busca = el("input", {
    type: "search",
    class: "entrada",
    id: `${prefixo}-busca-marca`,
    name: "busca-marca",
    autocomplete: "off",
    spellcheck: "false",
    placeholder: `Buscar entre ${marcas.length} marcas`,
    "aria-label": "Buscar marca",
  });
  const blocoBusca = el("div", { class: "ft-busca" }, icone("busca", "ic-sm"), busca);
  const grade = el("div", { class: "si-grade", role: "group", "aria-label": "Opções de ícone" });
  const nota = el("p", { class: "ft-cats-nota", "aria-live": "polite" });
  const automatico = el("button", { type: "button", class: "btn btn-texto si-auto" }, icone("ajustes", "ic-sm"), "Voltar ao automático");
  const bloco = el("div", { class: "si-bloco", id: `${prefixo}-seletor-icone` }, el("div", { class: "cg-abas si-abas", role: "group", "aria-label": "Tipo de ícone" }, ...abas), blocoBusca, grade, nota, automatico);

  function escolher(codigo, botao) {
    estado.codigo = estado.codigo === codigo ? null : codigo;
    grade.querySelectorAll(".si-opcao").forEach((b) => b.setAttribute("aria-pressed", String(b === botao && estado.codigo !== null)));
    automatico.hidden = estado.codigo === null;
    aoMudar?.(estado.codigo);
  }

  function opcao(codigo, rotulo, caixa) {
    const botao = el("button", { type: "button", class: "si-opcao", "aria-pressed": String(estado.codigo === codigo), "aria-label": rotulo, title: rotulo }, caixa);
    botao.addEventListener("click", () => escolher(codigo, botao));
    return botao;
  }

  function desenhar() {
    blocoBusca.hidden = estado.aba !== "marcas";
    grade.replaceChildren();
    automatico.hidden = estado.codigo === null;
    if (estado.aba === "icones") {
      const cat = categoriaAtual?.() ?? null;
      for (const [id, rotulo] of ICONES) grade.append(opcao(id, rotulo, caixaDoSimbolo(id, cat)));
      nota.textContent = "";
      return;
    }
    const termo = normalizar(estado.busca);
    let lista = termo ? marcas.filter((m) => normalizar(m.nome).includes(termo) || m.chaves.some((c) => normalizar(c).includes(termo))) : marcas.slice(0, MARCAS_SEM_BUSCA);
    const atual = estado.codigo?.startsWith("m-") ? marcaPorId(estado.codigo.slice(2)) : null;
    if (!termo && atual && !lista.includes(atual)) lista = [atual, ...lista];
    for (const marca of lista) grade.append(opcao(`m-${marca.id}`, marca.nome, caixaDaMarca(marca)));
    if (termo) nota.textContent = lista.length ? `${lista.length} ${lista.length === 1 ? "marca encontrada" : "marcas encontradas"}.` : `Nenhuma marca com “${estado.busca.trim()}”. Experimente outro nome ou use um ícone.`;
    else nota.textContent = "";
  }

  busca.addEventListener("input", () => {
    estado.busca = busca.value;
    desenhar();
  });
  busca.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      grade.querySelector(".si-opcao")?.click();
    }
  });
  automatico.addEventListener("click", () => {
    estado.codigo = null;
    desenhar();
    aoMudar?.(null);
    busca.focus();
  });

  desenhar();
  return {
    bloco,
    valor: () => estado.codigo,
    redesenhar: desenhar,
    focar: () => (estado.aba === "marcas" ? busca : grade.querySelector(".si-opcao"))?.focus(),
  };
}
