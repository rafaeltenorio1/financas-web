import { api } from "./api.js";
import { el, icone } from "./dom.js";
import { carregarCategorias, corDaCategoria, simboloDaCategoria } from "./categorias.js";
import { hoje, inicioDoMes, somarMeses } from "./datas.js";

const SUGESTOES = {
  despesa: ["Supermercado/Feira", "Restaurantes e Lanchonetes", "Delivery", "Combustível", "Aplicativos de Corridas", "Farmácia e Medicamentos", "Energia Elétrica", "Aluguel"],
  receita: ["Salário", "Freelance e Trabalhos Extras", "Rendimentos de Investimentos", "Vendas", "Reembolsos", "Presentes Recebidos", "Outras Receitas"],
};
const VISIVEIS = 8;
const normalizar = (texto) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

let usoCache = null;

export function esquecerUsoDasCategorias() {
  usoCache = null;
}

async function usoDasCategorias(fuso) {
  if (usoCache) return usoCache;
  const atual = hoje(fuso);
  const parametros = new URLSearchParams({
    data_inicio: inicioDoMes(somarMeses(atual, -2), fuso).toISOString(),
    data_fim: inicioDoMes(somarMeses(atual, 1), fuso).toISOString(),
    fuso,
  });
  const resumo = await api.get(`/transacoes/resumo?${parametros}`);
  usoCache = new Map(resumo.por_categoria.filter((c) => c.id_categoria).map((c) => [`${c.tipo}:${c.id_categoria}`, c.quantidade]));
  return usoCache;
}

export function criarSeletorDeCategorias({ prefixo, tipo, selecionada = null, rotuladoPor }) {
  const estado = { tipo, categoria: selecionada, busca: "", todas: false };
  let categorias = [];
  let uso = new Map();

  const busca = el("input", {
    type: "search",
    class: "entrada",
    id: `${prefixo}-busca`,
    name: "busca-categoria",
    autocomplete: "off",
    placeholder: "Buscar categoria",
    "aria-label": "Buscar categoria",
    spellcheck: "false",
  });
  const grade = el("div", { class: "ft-cats", role: "group", "aria-labelledby": rotuladoPor });
  const nota = el("p", { class: "ft-cats-nota", "aria-live": "polite" });
  const gerenciar = el("a", { class: "ft-cats-gerenciar", href: "#/categorias" }, icone("categorias", "ic-sm"), "Criar ou editar categorias");
  gerenciar.addEventListener("click", (evento) => {
    const dialogo = gerenciar.closest("dialog");
    if (!dialogo) return;
    evento.preventDefault();
    if (!dialogo.dispatchEvent(new Event("cancel", { cancelable: true }))) return;
    dialogo.close();
    location.hash = "#/categorias";
  });
  const bloco = el("div", {}, el("div", { class: "ft-busca" }, icone("busca", "ic-sm"), busca), grade, nota, gerenciar);

  function doTipo() {
    return categorias.filter((c) => !c.tipo_padrao || c.tipo_padrao === estado.tipo);
  }

  function semBusca(lista) {
    const chave = (c) => `${estado.tipo}:${c.id_categoria}`;
    const usadas = lista.filter((c) => uso.has(chave(c))).sort((a, b) => uso.get(chave(b)) - uso.get(chave(a)));
    const escolhidas = [...usadas];
    for (const nome of SUGESTOES[estado.tipo]) {
      const achada = lista.find((c) => c.nome === nome);
      if (achada && !escolhidas.includes(achada)) escolhidas.push(achada);
    }
    for (const c of lista) if (escolhidas.length < VISIVEIS && !escolhidas.includes(c)) escolhidas.push(c);
    const topo = escolhidas.slice(0, VISIVEIS);
    const atual = lista.find((c) => c.id_categoria === estado.categoria);
    if (atual && !topo.includes(atual)) topo.unshift(atual);
    return { mostradas: topo, usouHistorico: usadas.length > 0 };
  }

  function desenhar() {
    const lista = doTipo().sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    const termo = normalizar(estado.busca);
    let mostradas;
    nota.replaceChildren();
    if (termo) {
      mostradas = lista.filter((c) => normalizar(c.nome).includes(termo));
      nota.textContent = mostradas.length
        ? `${mostradas.length} ${mostradas.length === 1 ? "categoria encontrada" : "categorias encontradas"}.`
        : `Nenhuma categoria com “${estado.busca.trim()}”.`;
    } else if (estado.todas) {
      mostradas = lista;
      nota.textContent = `Todas as ${lista.length} categorias. Toque de novo na escolhida para tirar.`;
    } else {
      const resultado = semBusca(lista);
      mostradas = resultado.mostradas;
      const verTodas = el("button", { type: "button", texto: `ver todas as ${lista.length}` });
      verTodas.addEventListener("click", () => {
        estado.todas = true;
        desenhar();
        grade.querySelector("button")?.focus();
      });
      nota.append(resultado.usouHistorico ? "Suas mais usadas. Busque ou " : "Algumas sugestões. Busque ou ", verTodas, ".");
    }
    grade.replaceChildren();
    for (const cat of mostradas) {
      const botao = el(
        "button",
        { type: "button", class: "ft-cat", "aria-pressed": String(cat.id_categoria === estado.categoria), title: cat.nome },
        el("span", { class: "ft-cat-ic", "aria-hidden": "true" }, icone(simboloDaCategoria(cat))),
        el("span", { texto: cat.nome }),
      );
      botao.style.setProperty("--cor", corDaCategoria(cat));
      botao.addEventListener("click", () => {
        estado.categoria = estado.categoria === cat.id_categoria ? null : cat.id_categoria;
        grade.querySelectorAll(".ft-cat").forEach((b) => b.setAttribute("aria-pressed", String(b === botao && estado.categoria !== null)));
      });
      grade.append(botao);
    }
  }

  busca.addEventListener("input", () => {
    estado.busca = busca.value;
    desenhar();
  });
  busca.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      grade.querySelector(".ft-cat")?.click();
    }
  });

  return {
    bloco,
    valor: () => estado.categoria,
    definirTipo(novo) {
      estado.tipo = novo;
      const atual = categorias.find((c) => c.id_categoria === estado.categoria);
      if (atual?.tipo_padrao && atual.tipo_padrao !== novo) estado.categoria = null;
      if (categorias.length) desenhar();
    },
    async carregar(fuso) {
      try {
        const [mapa, usoCarregado] = await Promise.all([carregarCategorias(), usoDasCategorias(fuso).catch(() => new Map())]);
        categorias = [...mapa.values()];
        uso = usoCarregado;
        if (bloco.isConnected) desenhar();
      } catch {
        nota.textContent = "Não foi possível carregar as categorias. Você pode salvar sem categoria.";
      }
    },
  };
}
