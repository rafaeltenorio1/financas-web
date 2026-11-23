import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { usuarioAtual } from "./sessao.js";
import { carregarCategorias, corDaCategoria, simboloDaCategoria } from "./categorias.js";
import { chaveDoDia, chaveDoMes, diaNoFuso, hoje, inicioDoMes, instanteLocal, lerChaveDoDia, somarDias, somarMeses } from "./datas.js";
import { moeda } from "./formatos.js";
import { avisar } from "./avisos.js";

const FORMAS = [
  ["pix", "Pix"],
  ["cartao de credito", "Cartão de crédito"],
  ["cartao de debito", "Cartão de débito"],
  ["boleto", "Boleto"],
  ["dinheiro", "Dinheiro"],
];
const SUGESTOES = {
  despesa: ["Supermercado/Feira", "Restaurantes e Lanchonetes", "Delivery", "Combustível", "Aplicativos de Corridas", "Farmácia e Medicamentos", "Energia Elétrica", "Aluguel"],
  receita: ["Salário", "Freelance e Trabalhos Extras", "Rendimentos de Investimentos", "Vendas", "Reembolsos", "Presentes Recebidos", "Outras Receitas"],
};
const VISIVEIS = 8;
const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });
const normalizar = (texto) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

let usoCache = null;
const resumoCache = new Map();

export function esquecerCachesDoFormulario() {
  usoCache = null;
  resumoCache.clear();
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

async function resumoDoMes(mes, fuso) {
  const chave = chaveDoMes(mes);
  if (!resumoCache.has(chave)) {
    const parametros = new URLSearchParams({
      data_inicio: inicioDoMes(mes, fuso).toISOString(),
      data_fim: inicioDoMes(somarMeses(mes, 1), fuso).toISOString(),
      fuso,
    });
    resumoCache.set(chave, api.get(`/transacoes/resumo?${parametros}`).catch((erro) => {
      resumoCache.delete(chave);
      throw erro;
    }));
  }
  return resumoCache.get(chave);
}

function formatarCentavos(digitos) {
  return moeda(Number(digitos || "0") / 100);
}

export async function abrirFormularioTransacao({ transacao = null, aoSalvar, aoFechar } = {}) {
  const usuario = usuarioAtual();
  const fuso = usuario?.fuso ?? "America/Sao_Paulo";
  const editando = transacao !== null;
  const origemDoFoco = document.activeElement;
  const hojeLocal = hoje(fuso);
  const ontemLocal = somarDias(hojeLocal, -1);
  const diaOriginal = editando ? diaNoFuso(transacao.data_hora, fuso) : null;

  const estado = {
    tipo: transacao?.tipo ?? "despesa",
    centavos: editando ? String(Math.round(Number(transacao.valor) * 100)) : "",
    quando: "hoje",
    outraData: "",
    categoria: transacao?.id_categoria ?? null,
    forma: transacao?.forma_pagamento ?? null,
    busca: "",
    todas: false,
  };
  if (diaOriginal) {
    const chave = chaveDoDia(diaOriginal);
    estado.quando = chave === chaveDoDia(hojeLocal) ? "hoje" : chave === chaveDoDia(ontemLocal) ? "ontem" : "outra";
    estado.outraData = chave;
  }

  let categorias = [];
  let uso = new Map();
  const titulo = editando ? "Editar transação" : "Nova transação";

  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
  const botoesTipo = [
    ["despesa", "Gasto", "sai"],
    ["receita", "Ganho", "entra"],
  ].map(([tipo, rotulo, simbolo]) => {
    const botao = el("button", { type: "button", class: tipo, "aria-pressed": "false" }, icone(simbolo, "ic-sm"), rotulo);
    botao.addEventListener("click", () => mudarTipo(tipo));
    return botao;
  });
  const ajudaValor = el("p", { class: "campo-ajuda", id: "ft-valor-ajuda", texto: "Digite só os números: 4590 vira R$ 45,90." });
  const erroValor = el("p", { class: "campo-erro", id: "ft-valor-erro" });
  const valor = el("input", {
    id: "ft-valor",
    name: "valor",
    inputmode: "numeric",
    autocomplete: "off",
    "aria-describedby": "ft-valor-ajuda ft-valor-erro",
    value: formatarCentavos(estado.centavos),
  });
  const nome = el("input", { class: "entrada", id: "ft-nome", name: "nome", maxlength: 255, autocomplete: "off", placeholder: "Ex.: Mercado do mês" });
  nome.value = transacao?.nome ?? "";

  const chipsQuando = el("div", { class: "ft-chips", role: "group", "aria-label": "Data" });
  const dataOutra = el("input", { type: "date", class: "entrada ft-data", id: "ft-data", name: "data", "aria-label": "Escolher data", max: chaveDoDia(somarDias(hojeLocal, 366)) });
  dataOutra.value = estado.outraData;
  const erroData = el("p", { class: "campo-erro", id: "ft-data-erro" });
  dataOutra.setAttribute("aria-describedby", "ft-data-erro");

  const busca = el("input", { type: "search", class: "entrada", id: "ft-busca", name: "busca", autocomplete: "off", placeholder: "Buscar categoria", "aria-label": "Buscar categoria", spellcheck: "false" });
  const grade = el("div", { class: "ft-cats", role: "group", "aria-labelledby": "ft-titulo-categoria" });
  const notaCategorias = el("p", { class: "ft-cats-nota", "aria-live": "polite" });
  const chipsForma = el("div", { class: "ft-chips", role: "group", "aria-labelledby": "ft-titulo-forma" });
  const descricao = el("textarea", { class: "entrada", id: "ft-descricao", name: "descricao", maxlength: 1000, "aria-label": "Observação" });
  descricao.value = transacao?.descricao ?? "";
  const observacao = el("details", {}, el("summary", { texto: "Adicionar observação" }), descricao);
  if (descricao.value) observacao.open = true;

  const impacto = el("p", { class: "ft-impacto", "aria-live": "polite" });
  const avisoErro = el("div", { class: "mensagem", role: "alert" });
  const salvar = el("button", { type: "submit", class: "btn btn-primario" });

  const formulario = el(
    "form",
    { novalidate: true },
    el(
      "div",
      { class: "ft-corpo" },
      el("div", { class: "ft-topo" }, fechar, el("h2", { id: "ft-titulo", texto: titulo })),
      el(
        "div",
        { class: "ft-valor" },
        el("div", { class: "ft-tipo", role: "group", "aria-label": "Tipo" }, ...botoesTipo),
        el("label", { for: "ft-valor", texto: "Valor" }),
        valor,
        ajudaValor,
        erroValor,
      ),
      el("div", { class: "ft-secao campo" }, el("label", { class: "ft-rotulo", for: "ft-nome", texto: "Descrição" }), nome),
      el("div", { class: "ft-secao" }, el("h3", { texto: "Quando" }), chipsQuando, dataOutra, erroData),
      el(
        "div",
        { class: "ft-secao" },
        el("h3", { id: "ft-titulo-categoria", texto: "Categoria" }),
        el("div", { class: "ft-busca" }, icone("busca", "ic-sm"), busca),
        grade,
        notaCategorias,
      ),
      el("div", { class: "ft-secao" }, el("h3", { id: "ft-titulo-forma", texto: "Como pagou" }), chipsForma),
      el("div", { class: "ft-secao" }, observacao),
    ),
    el("div", { class: "ft-rodape" }, avisoErro, impacto, salvar),
  );
  const dialogo = el("dialog", { class: "form-transacao", "aria-labelledby": "ft-titulo" }, formulario);

  function desenharQuando() {
    chipsQuando.replaceChildren();
    for (const [chave, rotulo] of [["hoje", "Hoje"], ["ontem", "Ontem"], ["outra", "Outra data"]]) {
      const chip = el("button", { type: "button", class: "ft-chip", "aria-pressed": String(estado.quando === chave), texto: rotulo });
      chip.addEventListener("click", () => {
        estado.quando = chave;
        desenharQuando();
        agendarImpacto();
        if (chave === "outra") dataOutra.focus();
      });
      chipsQuando.append(chip);
    }
    dataOutra.hidden = estado.quando !== "outra";
    if (estado.quando !== "outra") marcarErroData("");
  }

  function desenharFormas() {
    chipsForma.replaceChildren();
    for (const [chave, rotulo] of FORMAS) {
      const chip = el("button", { type: "button", class: "ft-chip", "aria-pressed": String(estado.forma === chave), texto: rotulo });
      chip.addEventListener("click", () => {
        estado.forma = estado.forma === chave ? null : chave;
        desenharFormas();
        chipsForma.querySelectorAll("button")[FORMAS.findIndex(([c]) => c === chave)].focus();
      });
      chipsForma.append(chip);
    }
  }

  function categoriasDoTipo() {
    return categorias.filter((c) => !c.tipo_padrao || c.tipo_padrao === estado.tipo);
  }

  function visiveisSemBusca(lista) {
    const usadas = lista
      .filter((c) => uso.has(`${estado.tipo}:${c.id_categoria}`))
      .sort((a, b) => uso.get(`${estado.tipo}:${b.id_categoria}`) - uso.get(`${estado.tipo}:${a.id_categoria}`));
    const escolhidas = [...usadas];
    for (const nomeSugerido of SUGESTOES[estado.tipo]) {
      const achada = lista.find((c) => c.nome === nomeSugerido);
      if (achada && !escolhidas.includes(achada)) escolhidas.push(achada);
    }
    for (const c of lista) if (escolhidas.length < VISIVEIS && !escolhidas.includes(c)) escolhidas.push(c);
    const topo = escolhidas.slice(0, VISIVEIS);
    const selecionada = lista.find((c) => c.id_categoria === estado.categoria);
    if (selecionada && !topo.includes(selecionada)) topo.unshift(selecionada);
    return { mostradas: topo, usouHistorico: usadas.length > 0 };
  }

  function desenharCategorias() {
    const lista = categoriasDoTipo().sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    const termo = normalizar(estado.busca);
    let mostradas;
    notaCategorias.replaceChildren();
    if (termo) {
      mostradas = lista.filter((c) => normalizar(c.nome).includes(termo));
      notaCategorias.textContent = mostradas.length ? `${mostradas.length} ${mostradas.length === 1 ? "categoria encontrada" : "categorias encontradas"}.` : `Nenhuma categoria com “${estado.busca.trim()}”.`;
    } else if (estado.todas) {
      mostradas = lista;
      notaCategorias.textContent = `Todas as ${lista.length} categorias. Toque de novo na escolhida para tirar.`;
    } else {
      const resultado = visiveisSemBusca(lista);
      mostradas = resultado.mostradas;
      const verTodas = el("button", { type: "button", texto: `ver todas as ${lista.length}` });
      verTodas.addEventListener("click", () => {
        estado.todas = true;
        desenharCategorias();
        grade.querySelector("button")?.focus();
      });
      notaCategorias.append(resultado.usouHistorico ? "Suas mais usadas. Busque ou " : "Algumas sugestões. Busque ou ", verTodas, ".");
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

  function mudarTipo(tipo) {
    estado.tipo = tipo;
    dialogo.dataset.tipo = tipo;
    botoesTipo.forEach((b) => b.setAttribute("aria-pressed", String(b.classList.contains(tipo))));
    salvar.textContent = editando ? "Salvar alterações" : tipo === "despesa" ? "Salvar gasto" : "Salvar ganho";
    const atual = categorias.find((c) => c.id_categoria === estado.categoria);
    if (atual?.tipo_padrao && atual.tipo_padrao !== tipo) estado.categoria = null;
    desenharCategorias();
    agendarImpacto();
  }

  function diaEscolhido() {
    if (estado.quando === "hoje") return hojeLocal;
    if (estado.quando === "ontem") return ontemLocal;
    return lerChaveDoDia(dataOutra.value);
  }

  function dataHoraEscolhida() {
    const dia = diaEscolhido();
    if (!dia) return null;
    if (editando && chaveDoDia(dia) === chaveDoDia(diaOriginal)) return transacao.data_hora;
    if (chaveDoDia(dia) === chaveDoDia(hojeLocal)) return new Date().toISOString();
    return instanteLocal({ ...dia, hora: 12 }, fuso).toISOString();
  }

  let temporizadorImpacto = null;
  function agendarImpacto() {
    clearTimeout(temporizadorImpacto);
    temporizadorImpacto = setTimeout(desenharImpacto, 300);
  }

  async function desenharImpacto() {
    const centavos = Number(estado.centavos || "0");
    const dia = diaEscolhido();
    if (!centavos || !dia) {
      impacto.replaceChildren();
      impacto.classList.remove("alerta");
      return;
    }
    const mes = { ano: dia.ano, mes: dia.mes };
    const pedido = `${estado.tipo}:${centavos}:${chaveDoMes(mes)}`;
    impacto.dataset.pedido = pedido;
    let resumo;
    try {
      resumo = await resumoDoMes(mes, fuso);
    } catch {
      impacto.replaceChildren();
      return;
    }
    if (impacto.dataset.pedido !== pedido) return;
    const campo = estado.tipo === "despesa" ? "despesas" : "receitas";
    let antes = Number(resumo[campo]);
    if (editando && transacao.tipo === estado.tipo && chaveDoMes(diaOriginal) === chaveDoMes(mes)) antes -= Number(transacao.valor);
    const depois = antes + centavos / 100;
    const nomeMes = nomeDoMes.format(new Date(Date.UTC(mes.ano, mes.mes - 1, 15)));
    const rotulo = estado.tipo === "despesa" ? "Gastos" : "Ganhos";
    impacto.replaceChildren(`${rotulo} de ${nomeMes} passam de ${moeda(antes)} para `, el("strong", { texto: moeda(depois) }), ".");
    const passouDoQueEntrou = estado.tipo === "despesa" && Number(resumo.receitas) > 0 && depois > Number(resumo.receitas);
    impacto.classList.toggle("alerta", passouDoQueEntrou);
    if (passouDoQueEntrou) impacto.append(" Fica acima do que entrou no mês.");
  }

  function marcarErroValor(texto) {
    erroValor.textContent = texto;
    if (texto) valor.setAttribute("aria-invalid", "true");
    else valor.removeAttribute("aria-invalid");
  }

  function marcarErroData(texto) {
    erroData.textContent = texto;
    if (texto) dataOutra.setAttribute("aria-invalid", "true");
    else dataOutra.removeAttribute("aria-invalid");
  }

  const inicial = () => JSON.stringify([estado.tipo, estado.centavos, estado.quando, dataOutra.value, estado.categoria, estado.forma, nome.value, descricao.value]);
  const snapshot = inicial();
  const alterado = () => inicial() !== snapshot;

  function podeFechar() {
    return !alterado() || confirm(editando ? "Descartar as alterações desta transação?" : "Descartar esta transação sem salvar?");
  }

  valor.addEventListener("input", () => {
    estado.centavos = valor.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 11);
    valor.value = formatarCentavos(estado.centavos);
    valor.setSelectionRange(valor.value.length, valor.value.length);
    marcarErroValor("");
    agendarImpacto();
  });
  valor.addEventListener("focus", () => requestAnimationFrame(() => valor.setSelectionRange(valor.value.length, valor.value.length)));
  dataOutra.addEventListener("input", () => {
    marcarErroData("");
    agendarImpacto();
  });
  busca.addEventListener("input", () => {
    estado.busca = busca.value;
    desenharCategorias();
  });
  busca.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter") {
      evento.preventDefault();
      grade.querySelector(".ft-cat")?.click();
    }
  });
  fechar.addEventListener("click", () => {
    if (podeFechar()) dialogo.close();
  });
  dialogo.addEventListener("cancel", (evento) => {
    if (!podeFechar()) evento.preventDefault();
  });
  dialogo.addEventListener("close", () => {
    clearTimeout(temporizadorImpacto);
    dialogo.remove();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
    aoFechar?.(dialogo.returnValue === "salvo");
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(avisoErro, "erro", "");
    const centavos = Number(estado.centavos || "0");
    marcarErroValor(centavos > 0 ? "" : "Informe um valor maior que zero.");
    const dataHora = dataHoraEscolhida();
    marcarErroData(estado.quando === "outra" && !dataHora ? "Escolha a data." : "");
    if (!centavos) return valor.focus();
    if (!dataHora) return dataOutra.focus();

    const corpo = {
      tipo: estado.tipo,
      valor: (centavos / 100).toFixed(2),
      data_hora: dataHora,
      nome: nome.value.trim() || null,
      id_categoria: estado.categoria,
      forma_pagamento: estado.forma,
      descricao: descricao.value.trim() || null,
    };
    ocupado(salvar, true, "Salvando…");
    try {
      const salva = editando ? await api.patch(`/transacoes/${transacao.id_transacao}`, corpo) : await api.post("/transacoes", corpo);
      esquecerCachesDoFormulario();
      dialogo.close("salvo");
      const rotulo = `${salva.tipo === "despesa" ? "Gasto" : "Ganho"} de ${moeda(salva.valor)}`;
      avisar(editando ? `${rotulo} atualizado.` : `${rotulo} salvo.`, {
        acao: editando
          ? undefined
          : {
              texto: "Desfazer",
              executar: async () => {
                try {
                  await api.delete(`/transacoes/${salva.id_transacao}`);
                  esquecerCachesDoFormulario();
                  avisar("Transação desfeita.");
                  aoSalvar?.(null);
                } catch (erro) {
                  avisar(erro.message, { tipo: "erro" });
                }
              },
            },
      });
      aoSalvar?.(salva);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.campos.valor) {
        marcarErroValor("Confira o valor.");
        valor.focus();
      } else if (erro.campos.data_hora) {
        estado.quando = "outra";
        desenharQuando();
        marcarErroData("Confira a data.");
        dataOutra.focus();
      } else {
        mensagem(avisoErro, "erro", erro.status === 422 && /categoria/i.test(erro.message) ? "Essa categoria não está mais disponível. Escolha outra." : erro.message);
      }
    } finally {
      if (dialogo.isConnected) ocupado(salvar, false);
    }
  });

  document.body.append(dialogo);
  mudarTipo(estado.tipo);
  desenharQuando();
  desenharFormas();
  dialogo.showModal();
  if (matchMedia("(min-width: 900px)").matches) valor.focus();

  try {
    const [mapa, usoCarregado] = await Promise.all([carregarCategorias(), usoDasCategorias(fuso).catch(() => new Map())]);
    categorias = [...mapa.values()];
    uso = usoCarregado;
    if (dialogo.isConnected) desenharCategorias();
  } catch {
    notaCategorias.textContent = "Não foi possível carregar as categorias. Você pode salvar sem categoria.";
  }
  agendarImpacto();
  return dialogo;
}
