import { api } from "../api.js";
import { el, icone } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { carregarCategorias, corDaCategoria, simboloDaCategoria } from "../categorias.js";
import { abrirFormularioCategoria, PASTEIS } from "../categoria-form.js";
import { chaveDoMes, hoje, inicioDoMes, somarMeses } from "../datas.js";
import { moeda } from "../formatos.js";

const ABAS = [
  ["todas", "Todas"],
  ["despesa", "Gastos"],
  ["receita", "Ganhos"],
];
const TIPOS_VALIDOS = new Set(ABAS.map(([tipo]) => tipo));
const normalizar = (texto) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

export async function montar(raiz, { parametros }) {
  const fuso = usuarioAtual().fuso;
  const mes = hoje(fuso);
  const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(mes.ano, mes.mes - 1, 1)));
  const estado = {
    tipo: TIPOS_VALIDOS.has(parametros.get("tipo")) ? parametros.get("tipo") : "todas",
    busca: "",
    categorias: [],
    totais: new Map(),
    totaisFalharam: false,
  };

  const nova = el("button", { type: "button", class: "btn btn-primario" }, icone("mais", "ic-sm"), "Nova categoria");
  const abas = ABAS.map(([tipo, rotulo]) => {
    const botao = el("button", { type: "button", "aria-pressed": String(tipo === estado.tipo), texto: rotulo });
    botao.addEventListener("click", () => escolherTipo(tipo));
    return botao;
  });
  const busca = el("input", { type: "search", class: "entrada", id: "cg-busca", name: "busca", autocomplete: "off", spellcheck: "false", maxlength: 100, placeholder: "Buscar categoria", "aria-label": "Buscar categoria" });
  const anuncio = el("p", { class: "sr", "aria-live": "polite" });
  const conteudo = el("div", { class: "cg-conteudo", "aria-busy": "true" }, el("p", { class: "cg-carregando", texto: "Carregando categorias…" }));

  raiz.append(
    el("header", { class: "ct-cab" }, el("h1", { texto: "Categorias" }), nova),
    el(
      "div",
      { class: "cg-barra" },
      el("div", { class: "cg-abas", role: "group", "aria-label": "Tipo de categoria" }, ...abas),
      el("div", { class: "ft-busca cg-busca" }, icone("busca", "ic-sm"), busca),
    ),
    anuncio,
    conteudo,
  );

  function escolherTipo(tipo) {
    if (tipo === estado.tipo) return;
    estado.tipo = tipo;
    abas.forEach((b, i) => b.setAttribute("aria-pressed", String(ABAS[i][0] === tipo)));
    history.replaceState(null, "", `#/categorias${tipo === "todas" ? "" : `?tipo=${tipo}`}`);
    desenhar();
  }

  function corSugerida() {
    const minhas = estado.categorias.filter((c) => !c.padrao);
    const uso = new Map(PASTEIS.map(([hex]) => [hex, 0]));
    for (const c of minhas) if (uso.has(c.cor)) uso.set(c.cor, uso.get(c.cor) + 1);
    return [...uso.entries()].reduce((menor, atual) => (atual[1] < menor[1] ? atual : menor))[0];
  }

  function abrirEditor(categoria = null) {
    abrirFormularioCategoria({
      categoria,
      tipo: estado.tipo === "todas" ? "despesa" : estado.tipo,
      corSugerida: corSugerida(),
      aoSalvar: (salva) => recarregar(salva.id_categoria),
      aoApagar: () => recarregar(),
    });
  }
  nova.addEventListener("click", () => abrirEditor());

  function textoDoMes(cat) {
    if (estado.totaisFalharam) return "";
    if (estado.tipo !== "todas") {
      const total = estado.totais.get(`${estado.tipo}:${cat.id_categoria}`);
      return total ? `${moeda(total)} em ${nomeDoMes}` : "";
    }
    const gasto = estado.totais.get(`despesa:${cat.id_categoria}`);
    const recebido = estado.totais.get(`receita:${cat.id_categoria}`);
    const partes = [gasto ? `${moeda(gasto)} gastos` : "", recebido ? `${moeda(recebido)} recebidos` : ""].filter(Boolean);
    return partes.length ? `${partes.join(" e ")} em ${nomeDoMes}` : "";
  }

  function ficha(cat, { editavel }) {
    const conteudoFicha = [
      el("span", { class: "ft-cat-ic", "aria-hidden": "true" }, icone(simboloDaCategoria(cat))),
      el(
        "span",
        { class: "cg-ficha-texto" },
        el("span", { class: "cg-ficha-nome", texto: cat.nome, title: cat.nome }),
        el("span", { class: "cg-ficha-mes", texto: textoDoMes(cat) }),
      ),
    ];
    let item;
    if (editavel) {
      item = el("button", { type: "button", class: "ft-cat cg-ficha cg-minha", "data-id": cat.id_categoria }, ...conteudoFicha);
      item.setAttribute("aria-label", [cat.nome, textoDoMes(cat), "Editar"].filter(Boolean).join(". "));
      item.addEventListener("click", () => abrirEditor(cat));
    } else {
      const q = new URLSearchParams({ mes: chaveDoMes(mes), categoria: cat.id_categoria });
      if (estado.tipo !== "todas") q.set("tipo", estado.tipo);
      item = el("a", { class: "ft-cat cg-ficha cg-padrao", href: `#/transacoes?${q}` }, ...conteudoFicha, icone("cadeado", "ic-sm cg-cadeado"));
      item.setAttribute("aria-label", [`${cat.nome}, categoria padrão`, textoDoMes(cat), "Ver transações"].filter(Boolean).join(". "));
    }
    item.style.setProperty("--cor", corDaCategoria(cat));
    return el("li", {}, item);
  }

  function fichaNova() {
    const botao = el("button", { type: "button", class: "ft-cat cg-ficha cg-nova" }, el("span", { class: "ft-cat-ic", "aria-hidden": "true" }, icone("mais")), el("span", { class: "cg-ficha-nome", texto: "Nova categoria" }));
    botao.addEventListener("click", () => abrirEditor());
    return el("li", {}, botao);
  }

  function desenhar() {
    const termo = normalizar(estado.busca);
    const doTipo = estado.categorias
      .filter((c) => estado.tipo === "todas" || !c.tipo_padrao || c.tipo_padrao === estado.tipo)
      .filter((c) => !termo || normalizar(c.nome).includes(termo))
      .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    const minhas = doTipo.filter((c) => !c.padrao);
    const padrao = doTipo.filter((c) => c.padrao);

    const secaoMinhas = el(
      "section",
      { class: "cg-secao", "aria-labelledby": "cg-titulo-minhas" },
      el("h2", { id: "cg-titulo-minhas" }, "Minhas", el("span", { class: "ct-contagem", texto: String(minhas.length) })),
    );
    const listaMinhas = el("ul", { class: "cg-grade" }, minhas.map((c) => ficha(c, { editavel: true })));
    if (!termo) listaMinhas.append(fichaNova());
    if (!termo && minhas.length === 0) {
      secaoMinhas.append(el("p", { class: "cg-nota", texto: estado.tipo !== "receita" ? "Crie categorias suas para o que as padrão não cobrem, como o nome do seu pet ou um hobby." : "Crie categorias suas para ganhos que as padrão não cobrem, como um aluguel que você recebe." }));
    }
    if (minhas.length || !termo) secaoMinhas.append(listaMinhas);
    else secaoMinhas.append(el("p", { class: "cg-nota", texto: "Nenhuma categoria sua com esse nome." }));

    const secaoPadrao = el(
      "section",
      { class: "cg-secao", "aria-labelledby": "cg-titulo-padrao" },
      el("h2", { id: "cg-titulo-padrao" }, "Padrão", el("span", { class: "ct-contagem", texto: String(padrao.length) })),
      el("p", { class: "cg-nota" }, icone("cadeado", "ic-sm"), "Vêm prontas e não podem ser editadas. Toque para ver as transações do mês."),
    );
    if (padrao.length) secaoPadrao.append(el("ul", { class: "cg-grade" }, padrao.map((c) => ficha(c, { editavel: false }))));
    else secaoPadrao.append(el("p", { class: "cg-nota", texto: "Nenhuma categoria padrão com esse nome." }));

    const blocos = [secaoMinhas, secaoPadrao];
    if (estado.totaisFalharam) blocos.unshift(el("p", { class: "mensagem mensagem-aviso" }, icone("alerta", "ic-sm"), el("span", { texto: "Não foi possível carregar os valores do mês. As categorias estão completas." })));
    conteudo.replaceChildren(...blocos);
    anuncio.textContent = termo ? `${minhas.length + padrao.length} ${minhas.length + padrao.length === 1 ? "categoria encontrada" : "categorias encontradas"}.` : "";
  }

  async function carregarTotais() {
    const q = new URLSearchParams({ data_inicio: inicioDoMes(mes, fuso).toISOString(), data_fim: inicioDoMes(somarMeses(mes, 1), fuso).toISOString(), fuso });
    try {
      const resumo = await api.get(`/transacoes/resumo?${q}`);
      estado.totais = new Map(resumo.por_categoria.filter((c) => c.id_categoria).map((c) => [`${c.tipo}:${c.id_categoria}`, Number(c.total)]));
      estado.totaisFalharam = false;
    } catch {
      estado.totaisFalharam = true;
    }
  }

  async function recarregar(focarId = null) {
    try {
      const [mapa] = await Promise.all([carregarCategorias({ forcar: true }), carregarTotais()]);
      estado.categorias = [...mapa.values()];
    } catch {
      if (!raiz.isConnected) return;
      const tentar = el("button", { type: "button", class: "btn btn-secundario", texto: "Tentar de novo" });
      tentar.addEventListener("click", () => {
        conteudo.replaceChildren(el("p", { class: "cg-carregando", texto: "Carregando categorias…" }));
        recarregar();
      });
      conteudo.removeAttribute("aria-busy");
      conteudo.replaceChildren(el("div", { class: "cg-erro" }, el("p", { class: "mensagem mensagem-erro" }, icone("erro", "ic-sm"), el("span", { texto: "Não foi possível carregar as categorias." })), tentar));
      return;
    }
    if (!raiz.isConnected) return;
    conteudo.removeAttribute("aria-busy");
    const salva = focarId && estado.categorias.find((c) => c.id_categoria === focarId);
    if (salva?.tipo_padrao && estado.tipo !== "todas" && salva.tipo_padrao !== estado.tipo) escolherTipo(salva.tipo_padrao);
    desenhar();
    if (focarId) conteudo.querySelector(`[data-id="${CSS.escape(focarId)}"]`)?.focus();
  }

  busca.addEventListener("input", () => {
    estado.busca = busca.value;
    desenhar();
  });

  await recarregar();
}
