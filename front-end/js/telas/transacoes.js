import { api, baixarArquivo, ErroApi } from "../api.js";
import { el, icone, ocupado } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { carregarCategorias, categoria, corDaCategoria } from "../categorias.js";
import { chaveDoDia, chaveDoMes, compararMeses, diaNoFuso, hoje, inicioDoMes, lerChaveDoMes, somarMeses } from "../datas.js";
import { dataLonga, hora, mesAno, moeda, moedaComSinal } from "../formatos.js";
import { iconeDaTransacao, nomeDaTransacao } from "../painel/componentes.js";
import { carregarIconesDasContas } from "../contas-icones.js";
import { abrirFormularioTransacao, esquecerCachesDoFormulario } from "../transacao-form.js";
import { avisar } from "../avisos.js";
import { confirmar } from "../confirmar.js";

const POR_PAGINA = 50;
const CHAVE_MODO = "transacoes-detalhe";
const FORMAS = {
  pix: "Pix",
  "cartao de credito": "Cartão de crédito",
  "cartao de debito": "Cartão de débito",
  boleto: "Boleto",
  dinheiro: "Dinheiro",
};
const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });

function lerModo() {
  try {
    return localStorage.getItem(CHAVE_MODO) === "embaixo" ? "embaixo" : "lado";
  } catch {
    return "lado";
  }
}

function guardarModo(modo) {
  try {
    localStorage.setItem(CHAVE_MODO, modo);
  } catch {}
}

function titulo(mes) {
  return mesAno(new Date(Date.UTC(mes.ano, mes.mes - 1, 15, 12)).toISOString());
}

export async function montar(raiz, { parametros, navegar }) {
  const usuario = usuarioAtual();
  const fuso = usuario.fuso;
  const hojeLocal = hoje(fuso);
  const mesAtual = { ano: hojeLocal.ano, mes: hojeLocal.mes };
  const desktop = matchMedia("(min-width: 900px)");

  let mesPedido = lerChaveDoMes(parametros.get("mes")) ?? mesAtual;
  if (compararMeses(mesPedido, mesAtual) > 0) mesPedido = mesAtual;
  const filtros = {
    mes: mesPedido,
    tipo: ["despesa", "receita"].includes(parametros.get("tipo")) ? parametros.get("tipo") : null,
    categoria: parametros.get("categoria") || null,
    busca: (parametros.get("busca") || "").slice(0, 100),
  };
  let modo = lerModo();
  let itens = [];
  let temMais = false;
  let resumo = null;
  let totaisApi = null;
  let aberta = null;
  let controle = null;
  let carregandoMais = false;

  const anuncio = el("p", { class: "sr", "aria-live": "polite" });
  const tituloMes = el("h1");
  const voltarMes = el("button", { type: "button", class: "painel-mes-seta", "aria-label": "Mês anterior" }, icone("anterior"));
  const avancarMes = el("button", { type: "button", class: "painel-mes-seta", "aria-label": "Próximo mês" }, icone("proximo"));
  const botoesModo = [
    ["lado", "layout-colunas", "Detalhe ao lado da lista"],
    ["embaixo", "layout-lista", "Detalhe embaixo da transação"],
  ].map(([valor, simbolo, rotulo]) => {
    const botao = el("button", { type: "button", title: rotulo, "aria-pressed": String(modo === valor) }, icone(simbolo, "ic-sm"), el("span", { texto: valor === "lado" ? "Ao lado" : "Embaixo" }));
    botao.addEventListener("click", () => {
      modo = valor;
      guardarModo(valor);
      botoesModo.forEach((b, i) => b.setAttribute("aria-pressed", String(["lado", "embaixo"][i] === modo)));
      desenharLista();
    });
    return botao;
  });
  const exportar = el("button", { type: "button", class: "btn btn-secundario", title: "Baixar as transações filtradas em CSV" }, icone("baixar", "ic-sm"), el("span", { class: "rotulo-curto", texto: "Exportar" }));
  exportar.setAttribute("aria-label", "Exportar transações filtradas em CSV");
  const importar = el("button", { type: "button", class: "btn btn-secundario", title: "Importar extrato do banco", "aria-haspopup": "dialog" }, icone("enviar", "ic-sm"), el("span", { class: "rotulo-curto", texto: "Importar" }));
  importar.setAttribute("aria-label", "Importar extrato do banco");
  importar.addEventListener("click", async () => {
    const { abrirImportacao } = await import("../importacao.js");
    abrirImportacao({ aoConcluir: () => navegar("/importar") });
  });
  const novaTransacao = el("button", { type: "button", class: "btn btn-primario tr-nova", "aria-haspopup": "dialog" }, icone("mais", "ic-sm"), "Nova transação");
  novaTransacao.addEventListener("click", () => abrirFormularioTransacao({ aoSalvar: () => carregar() }));

  const busca = el("input", { type: "search", class: "entrada", id: "tr-busca", name: "busca", autocomplete: "off", spellcheck: "false", maxlength: 100, placeholder: "Buscar", "aria-describedby": "tr-ajuda" });
  busca.value = filtros.busca;
  const botoesTipo = [
    [null, "Tudo"],
    ["despesa", "Gastos"],
    ["receita", "Ganhos"],
  ].map(([valor, rotulo]) => {
    const botao = el("button", { type: "button", "aria-pressed": String(filtros.tipo === valor), texto: rotulo });
    botao.addEventListener("click", () => {
      if (filtros.tipo === valor) return;
      filtros.tipo = valor;
      aplicarFiltros();
    });
    return botao;
  });
  const selectCategoria = el("select", { class: "entrada tr-cat-select", "aria-label": "Categoria" });
  selectCategoria.addEventListener("change", () => {
    filtros.categoria = selectCategoria.value || null;
    aplicarFiltros();
  });
  const listaCategorias = el("div", { class: "tr-cats", role: "group", "aria-label": "Categorias deste mês" });
  const limpar = el("button", { type: "button", class: "tr-limpar", texto: "Limpar filtros" });
  limpar.addEventListener("click", () => {
    filtros.tipo = null;
    filtros.categoria = null;
    filtros.busca = "";
    busca.value = "";
    aplicarFiltros();
    busca.focus();
  });
  const painelFiltros = el(
    "aside",
    { class: "tr-filtros", "aria-label": "Filtros" },
    el("div", { class: "tr-busca" }, icone("busca", "ic-sm"), el("label", { class: "sr", for: "tr-busca", texto: "Buscar transações" }), busca),
    el("p", { class: "tr-ajuda", id: "tr-ajuda", texto: "Procura no nome, na observação e na categoria." }),
    el("div", { class: "tr-tipos", role: "group", "aria-label": "Tipo" }, ...botoesTipo),
    selectCategoria,
    listaCategorias,
    limpar,
    el("div", { class: "tr-modo-bloco" }, el("p", { id: "tr-titulo-modo", texto: "Abrir detalhe" }), el("div", { class: "tr-modo", role: "group", "aria-labelledby": "tr-titulo-modo" }, ...botoesModo)),
  );
  const resumoEl = el("dl", { class: "tr-resumo" });
  const lista = el("div", { class: "tr-lista" });
  const mais = el("button", { type: "button", class: "btn btn-secundario tr-mais", texto: "Carregar mais" });
  const colunaDetalhe = el("aside", { class: "tr-coluna-detalhe", "aria-label": "Detalhe da transação" });
  const grade = el("div", { class: "tr-grade" }, painelFiltros, el("section", { "aria-label": "Lista de transações" }, resumoEl, lista, mais), colunaDetalhe);

  raiz.append(
    el(
      "header",
      { class: "tr-cab" },
      el("div", { class: "painel-mes" }, voltarMes, tituloMes, avancarMes),
      el("div", { class: "tr-acoes" }, exportar, importar, novaTransacao),
    ),
    anuncio,
    grade,
  );

  function periodo() {
    return { inicio: inicioDoMes(filtros.mes, fuso).toISOString(), fim: inicioDoMes(somarMeses(filtros.mes, 1), fuso).toISOString() };
  }

  function consultaDaLista(extra = {}) {
    const { inicio, fim } = periodo();
    const q = new URLSearchParams({ data_inicio: inicio, data_fim: fim, ...extra });
    if (filtros.tipo) q.set("tipo", filtros.tipo);
    if (filtros.categoria) q.set("id_categoria", filtros.categoria);
    if (filtros.busca.trim()) q.set("busca", filtros.busca.trim());
    return q;
  }

  function atualizarUrl() {
    const q = new URLSearchParams();
    if (compararMeses(filtros.mes, mesAtual) !== 0) q.set("mes", chaveDoMes(filtros.mes));
    if (filtros.tipo) q.set("tipo", filtros.tipo);
    if (filtros.categoria) q.set("categoria", filtros.categoria);
    if (filtros.busca.trim()) q.set("busca", filtros.busca.trim());
    history.replaceState(null, "", `#/transacoes${q.size ? `?${q}` : ""}`);
  }

  function desenharCabecalho() {
    tituloMes.textContent = titulo(filtros.mes);
    avancarMes.disabled = compararMeses(filtros.mes, mesAtual) >= 0;
    botoesTipo.forEach((b, i) => b.setAttribute("aria-pressed", String([null, "despesa", "receita"][i] === filtros.tipo)));
    limpar.hidden = !filtros.tipo && !filtros.categoria && !filtros.busca.trim();
  }

  function linhasDeCategoria() {
    if (!resumo) return [];
    return resumo.por_categoria
      .filter((c) => c.id_categoria && (!filtros.tipo || c.tipo === filtros.tipo))
      .map((c) => ({ ...c, total: Number(c.total), cat: categoria(c.id_categoria) ?? { nome: c.nome, cor: c.cor } }))
      .sort((a, b) => b.total - a.total);
  }

  function desenharCategorias() {
    const linhas = linhasDeCategoria();
    selectCategoria.replaceChildren(el("option", { value: "", texto: "Todas as categorias" }));
    listaCategorias.replaceChildren();
    const grupos = filtros.tipo ? [[filtros.tipo, null]] : [["despesa", "Gastos"], ["receita", "Ganhos"]];
    for (const [tipo, rotulo] of grupos) {
      const doTipo = linhas.filter((l) => l.tipo === tipo);
      if (!doTipo.length) continue;
      if (rotulo) listaCategorias.append(el("p", { class: "tr-cats-titulo", texto: rotulo }));
      else listaCategorias.append(el("p", { class: "tr-cats-titulo", texto: "Categorias deste mês" }));
      const grupoSelect = el("optgroup", { label: rotulo ?? "Categorias deste mês" });
      for (const linha of doTipo) {
        const escolhida = filtros.categoria === linha.id_categoria;
        const marcador = el("i");
        marcador.style.setProperty("--cor", corDaCategoria(linha.cat));
        const botao = el("button", { type: "button", class: "tr-cat", "aria-pressed": String(escolhida), title: linha.cat.nome }, marcador, el("span", { texto: linha.cat.nome }), el("small", { texto: moeda(linha.total) }));
        botao.addEventListener("click", () => {
          filtros.categoria = escolhida ? null : linha.id_categoria;
          aplicarFiltros();
        });
        listaCategorias.append(botao);
        grupoSelect.append(el("option", { value: linha.id_categoria, selected: escolhida, texto: `${linha.cat.nome} (${moeda(linha.total)})` }));
      }
      selectCategoria.append(grupoSelect);
    }
    if (!linhas.length) listaCategorias.append(el("p", { class: "tr-ajuda", texto: "Nenhuma categoria usada neste mês." }));
    if (filtros.categoria && !linhas.some((l) => l.id_categoria === filtros.categoria)) {
      const cat = categoria(filtros.categoria);
      selectCategoria.append(el("option", { value: filtros.categoria, selected: true, texto: cat?.nome ?? "Categoria escolhida" }));
    }
  }

  function desenharResumo() {
    resumoEl.replaceChildren();
    if (!totaisApi) return;
    if (filtros.tipo !== "receita") resumoEl.append(el("div", {}, el("dt", { texto: "Gastos" }), el("dd", { class: "despesa num", texto: moeda(totaisApi.despesas) })));
    if (filtros.tipo !== "despesa") resumoEl.append(el("div", {}, el("dt", { texto: "Ganhos" }), el("dd", { class: "receita num", texto: moeda(totaisApi.receitas) })));
    const n = totaisApi.quantidade;
    resumoEl.append(el("p", { class: "tr-resumo-nota", texto: `${n} ${n === 1 ? "transação" : "transações"}` }));
  }

  function diaDe(transacao) {
    return chaveDoDia(diaNoFuso(transacao.data_hora, fuso));
  }

  function contexto(transacao) {
    if (!resumo || !transacao.id_categoria) return null;
    const linha = resumo.por_categoria.find((c) => c.id_categoria === transacao.id_categoria && c.tipo === transacao.tipo);
    if (!linha) return null;
    const diaT = diaNoFuso(transacao.data_hora, fuso);
    if (chaveDoMes(diaT) !== chaveDoMes(filtros.mes)) return null;
    const nomeMes = nomeDoMes.format(new Date(Date.UTC(filtros.mes.ano, filtros.mes.mes - 1, 15)));
    const verbo = transacao.tipo === "despesa" ? "gastou" : "recebeu";
    return el(
      "p",
      { class: "tr-contexto" },
      `Em ${nomeMes} você ${verbo} `,
      el("strong", { texto: moeda(linha.total) }),
      ` em ${linha.nome}, ${linha.quantidade} ${linha.quantidade === 1 ? "transação" : "transações"}.`,
    );
  }

  function detalhe(transacao, idDetalhe) {
    const cat = categoria(transacao.id_categoria);
    const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar detalhe" }, icone("fechar", "ic-sm"));
    fechar.addEventListener("click", () => fecharDetalhe(true));
    const editar = el("button", { type: "button", class: "btn btn-primario", texto: "Editar" });
    editar.addEventListener("click", () => {
      abrirFormularioTransacao({
        transacao,
        aoSalvar: (salva) => {
          aberta = salva ? salva.id_transacao : null;
          carregar();
        },
      });
    });
    const apagar = el("button", { type: "button", class: "btn btn-secundario tr-apagar", texto: "Apagar" });
    apagar.addEventListener("click", async () => {
      const descricao = `${nomeDaTransacao(transacao)}, ${moeda(transacao.valor)}`;
      const sim = await confirmar({ titulo: "Apagar esta transação?", texto: `${descricao}. Não dá para desfazer.`, confirmar: "Apagar transação", perigo: true });
      if (!sim) return;
      ocupado(apagar, true, "Apagando…");
      try {
        await api.delete(`/transacoes/${transacao.id_transacao}`);
        esquecerCachesDoFormulario();
        aberta = null;
        avisar("Transação apagada.");
        carregar();
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        ocupado(apagar, false);
        avisar(erro.message, { tipo: "erro" });
      }
    });
    const itensDl = [
      ["Categoria", cat?.nome ?? "Sem categoria"],
      ["Pagamento", FORMAS[transacao.forma_pagamento] ?? "Não informado"],
      ["Data", `${dataLonga(transacao.data_hora)}, ${hora(transacao.data_hora)}`],
    ];
    const dl = el("dl", {}, itensDl.map(([rotulo, valor]) => el("div", {}, el("dt", { texto: rotulo }), el("dd", { texto: valor }))));
    const origem = transacao.id_conta_recorrente ? "Pagamento de uma conta recorrente." : transacao.id_externo ? "Importada de um extrato." : null;
    dl.append(el("div", { class: "inteiro" }, el("dt", { texto: "Observação" }), el("dd", { class: transacao.descricao ? "" : "suave", texto: transacao.descricao || "Sem observação." })));
    if (origem) dl.append(el("div", { class: "inteiro" }, el("dt", { texto: "Origem" }), el("dd", { class: "suave", texto: origem })));
    return el(
      "div",
      { class: "tr-detalhe", id: idDetalhe, role: "region", "aria-label": `Detalhe de ${nomeDaTransacao(transacao)}` },
      el(
        "div",
        { class: "tr-detalhe-topo" },
        el("div", {}, iconeDaTransacao(transacao), el("div", {}, el("h2", { texto: nomeDaTransacao(transacao) }), el("p", { texto: dataLonga(transacao.data_hora) }))),
        fechar,
      ),
      el("p", { class: `tr-detalhe-valor ${transacao.tipo}`, texto: moedaComSinal(transacao.valor, transacao.tipo) }),
      dl,
      el("div", { class: "tr-detalhe-botoes" }, editar, apagar),
      contexto(transacao),
    );
  }

  let transacaoExtra = null;

  function emColuna() {
    return desktop.matches && modo === "lado";
  }

  function desenharLista() {
    lista.replaceChildren();
    colunaDetalhe.replaceChildren();
    const abertaObj = itens.find((t) => t.id_transacao === aberta) ?? (transacaoExtra?.id_transacao === aberta ? transacaoExtra : null);
    grade.classList.toggle("com-coluna", Boolean(abertaObj) && emColuna());
    if (abertaObj && emColuna()) colunaDetalhe.append(detalhe(abertaObj, "tr-detalhe-aberto"));

    if (!itens.length) {
      const filtrado = filtros.tipo || filtros.categoria || filtros.busca.trim();
      const caixa = el("div", { class: "tr-vazio" });
      if (filtrado) {
        caixa.append(el("strong", { texto: "Nada encontrado com esses filtros." }), filtros.busca.trim() ? "A busca procura no nome, na observação e no nome da categoria." : "Tente outro tipo ou categoria.");
        const botao = el("button", { type: "button", class: "btn btn-secundario", texto: "Limpar filtros" });
        botao.addEventListener("click", () => limpar.click());
        caixa.append(el("br"), botao);
      } else {
        caixa.append(el("strong", { texto: `Nenhuma transação em ${nomeDoMes.format(new Date(Date.UTC(filtros.mes.ano, filtros.mes.mes - 1, 15)))}.` }), "Registre um gasto ou ganho para começar.");
        caixa.append(el("br"), el("a", { class: "btn btn-primario", href: "#/nova", texto: "Nova transação" }));
      }
      lista.append(caixa);
      mais.hidden = true;
      return;
    }

    const porDia = new Map();
    for (const t of itens) {
      const chave = diaDe(t);
      if (!porDia.has(chave)) porDia.set(chave, []);
      porDia.get(chave).push(t);
    }
    for (const doDia of porDia.values()) {
      const doTotal = totaisApi?.por_dia.find((d) => d.dia === diaDe(doDia[0]));
      const gastou = Number(doTotal?.despesas ?? 0);
      const entrou = Number(doTotal?.receitas ?? 0);
      const cabecalho = el("div", { class: "tr-dia-cab" }, el("h2", { texto: dataLonga(doDia[0].data_hora) }));
      if (gastou) cabecalho.append(el("span", { class: "tr-etiqueta", texto: `gastou ${moeda(gastou)}` }));
      if (entrou) cabecalho.append(el("span", { class: "tr-etiqueta", texto: `entrou ${moeda(entrou)}` }));
      const bloco = el("section", { class: "tr-dia", "aria-label": dataLonga(doDia[0].data_hora) }, cabecalho);
      for (const t of doDia) {
        const estaAberta = t.id_transacao === aberta;
        const idDetalhe = `detalhe-${t.id_transacao}`;
        const linha = el(
          "button",
          { type: "button", class: `tr-linha tx-${t.tipo}`, "aria-expanded": String(estaAberta), "aria-controls": estaAberta ? (emColuna() ? "tr-detalhe-aberto" : idDetalhe) : null },
          iconeDaTransacao(t),
          el("span", {}, el("span", { class: "tx-nome", texto: nomeDaTransacao(t), title: nomeDaTransacao(t) }), el("span", { class: "tx-meta", texto: [categoria(t.id_categoria)?.nome ?? "Sem categoria", FORMAS[t.forma_pagamento]].filter(Boolean).join(", ") })),
          el("span", { class: "sr", texto: t.tipo === "receita" ? "Receita" : "Despesa" }),
          el("span", { class: "tx-valor", texto: moedaComSinal(t.valor, t.tipo) }),
        );
        linha.dataset.id = t.id_transacao;
        linha.addEventListener("click", () => {
          aberta = estaAberta ? null : t.id_transacao;
          desenharLista();
          lista.querySelector(`.tr-linha[data-id="${t.id_transacao}"]`)?.focus();
        });
        bloco.append(linha);
        if (estaAberta && !emColuna()) bloco.append(detalhe(t, idDetalhe));
      }
      lista.append(bloco);
    }
    mais.hidden = !temMais;
    const restantes = (totaisApi?.quantidade ?? 0) - itens.length;
    if (temMais && restantes > 0) mais.textContent = `Carregar mais (${restantes} ${restantes === 1 ? "restante" : "restantes"})`;
  }

  function fecharDetalhe(devolverFoco) {
    if (!aberta) return;
    const id = aberta;
    aberta = null;
    transacaoExtra = null;
    desenharLista();
    if (devolverFoco) lista.querySelector(`.tr-linha[data-id="${id}"]`)?.focus();
  }

  function mostrarCarregando() {
    lista.replaceChildren(el("div", { class: "tr-carregando", "aria-hidden": "true" }, el("span", { class: "esqueleto" }), el("span", { class: "esqueleto" }), el("span", { class: "esqueleto" })));
    lista.setAttribute("aria-busy", "true");
    mais.hidden = true;
  }

  function mostrarErro(erro) {
    const tentar = el("button", { type: "button", class: "btn btn-secundario", texto: "Tentar de novo" });
    tentar.addEventListener("click", () => carregar());
    lista.replaceChildren(el("div", { class: "tr-vazio", role: "alert" }, el("strong", { texto: "Não foi possível carregar as transações." }), erro.message, el("br"), tentar));
  }

  async function carregar() {
    controle?.abort();
    controle = new AbortController();
    const sinal = controle.signal;
    desenharCabecalho();
    mostrarCarregando();
    const { inicio, fim } = periodo();
    try {
      const [pagina, resumoMes, totais] = await Promise.all([
        api.get(`/transacoes?${consultaDaLista({ limit: POR_PAGINA, offset: 0 })}`, { sinal }),
        api.get(`/transacoes/resumo?${new URLSearchParams({ data_inicio: inicio, data_fim: fim, fuso })}`, { sinal }),
        api.get(`/transacoes/totais?${consultaDaLista({ fuso })}`, { sinal }),
        carregarCategorias(),
        carregarIconesDasContas().catch(() => null),
      ]);
      itens = pagina;
      resumo = resumoMes;
      totaisApi = totais;
      temMais = itens.length < totais.quantidade;
    } catch (erro) {
      if (erro.name === "AbortError") return;
      lista.removeAttribute("aria-busy");
      mostrarErro(erro);
      return;
    }
    lista.removeAttribute("aria-busy");
    desenharCategorias();
    desenharResumo();
    desenharLista();
    anuncio.textContent = totaisApi.quantidade ? `${totaisApi.quantidade} ${totaisApi.quantidade === 1 ? "transação encontrada" : "transações encontradas"}.` : "Nenhuma transação encontrada.";
  }

  async function carregarMais() {
    if (carregandoMais) return;
    carregandoMais = true;
    ocupado(mais, true, "Carregando…");
    try {
      const pagina = await api.get(`/transacoes?${consultaDaLista({ limit: POR_PAGINA, offset: itens.length })}`, { sinal: controle?.signal });
      itens = [...itens, ...pagina];
      temMais = pagina.length === POR_PAGINA && itens.length < (totaisApi?.quantidade ?? Infinity);
      desenharResumo();
      desenharLista();
      anuncio.textContent = `Mais ${pagina.length} transações carregadas.`;
    } catch (erro) {
      if (erro.name !== "AbortError") avisar(erro.message, { tipo: "erro" });
    } finally {
      carregandoMais = false;
      ocupado(mais, false);
    }
  }

  function aplicarFiltros() {
    aberta = null;
    transacaoExtra = null;
    atualizarUrl();
    carregar();
  }

  let temporizadorBusca = null;
  busca.addEventListener("input", () => {
    clearTimeout(temporizadorBusca);
    temporizadorBusca = setTimeout(() => {
      filtros.busca = busca.value.slice(0, 100);
      aplicarFiltros();
    }, 350);
  });
  voltarMes.addEventListener("click", () => {
    filtros.mes = somarMeses(filtros.mes, -1);
    filtros.categoria = null;
    aplicarFiltros();
  });
  avancarMes.addEventListener("click", () => {
    if (compararMeses(filtros.mes, mesAtual) >= 0) return;
    filtros.mes = somarMeses(filtros.mes, 1);
    filtros.categoria = null;
    aplicarFiltros();
  });
  mais.addEventListener("click", carregarMais);
  exportar.addEventListener("click", async () => {
    ocupado(exportar, true, "Baixando…");
    try {
      const nome = await baixarArquivo(`/transacoes/exportar?${consultaDaLista()}`, "financas-transacoes.csv");
      avisar(`Arquivo ${nome} baixado.`);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.message, { tipo: "erro" });
    } finally {
      ocupado(exportar, false);
    }
  });

  function aoClicarFora(evento) {
    if (!aberta || document.querySelector("dialog[open]")) return;
    if (evento.target.closest(".tr-linha, .tr-detalhe, .aviso-flutuante")) return;
    fecharDetalhe(false);
  }
  function aoTeclar(evento) {
    if (evento.key === "Escape" && aberta && !document.querySelector("dialog[open]")) fecharDetalhe(true);
  }
  const aoMudarTela = () => desenharLista();
  document.addEventListener("pointerdown", aoClicarFora, true);
  document.addEventListener("keydown", aoTeclar);
  desktop.addEventListener("change", aoMudarTela);

  const idInicial = parametros.get("id");
  if (idInicial) {
    try {
      const transacao = await api.get(`/transacoes/${encodeURIComponent(idInicial)}`);
      const dia = diaNoFuso(transacao.data_hora, fuso);
      filtros.mes = { ano: dia.ano, mes: dia.mes };
      aberta = transacao.id_transacao;
      transacaoExtra = transacao;
      atualizarUrl();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.status === 404 ? "Essa transação não existe mais." : erro.message, { tipo: "erro" });
    }
  }
  await carregar();
  if (transacaoExtra && !itens.some((t) => t.id_transacao === aberta) && !emColuna()) {
    const alvo = transacaoExtra;
    abrirFormularioTransacao({ transacao: alvo, aoSalvar: () => carregar() });
  }

  return () => {
    controle?.abort();
    clearTimeout(temporizadorBusca);
    document.removeEventListener("pointerdown", aoClicarFora, true);
    document.removeEventListener("keydown", aoTeclar);
    desktop.removeEventListener("change", aoMudarTela);
  };
}
