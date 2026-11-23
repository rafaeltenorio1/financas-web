import { api, ErroApi } from "./api.js";
import { confirmar } from "./confirmar.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { usuarioAtual } from "./sessao.js";
import { criarSeletorDeCategorias, esquecerUsoDasCategorias } from "./seletor-categorias.js";
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
const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });

const resumoCache = new Map();

export function esquecerCachesDoFormulario() {
  esquecerUsoDasCategorias();
  resumoCache.clear();
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
    forma: transacao?.forma_pagamento ?? null,
  };
  if (diaOriginal) {
    const chave = chaveDoDia(diaOriginal);
    estado.quando = chave === chaveDoDia(hojeLocal) ? "hoje" : chave === chaveDoDia(ontemLocal) ? "ontem" : "outra";
    estado.outraData = chave;
  }

  const seletor = criarSeletorDeCategorias({ prefixo: "ft", tipo: estado.tipo, selecionada: transacao?.id_categoria ?? null, rotuladoPor: "ft-titulo-categoria" });
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
  const erroValor = el("p", { class: "campo-erro", id: "ft-valor-erro" });
  const valor = el("input", {
    id: "ft-valor",
    name: "valor",
    inputmode: "numeric",
    autocomplete: "off",
    "aria-describedby": "ft-valor-erro",
    value: formatarCentavos(estado.centavos),
  });
  const nome = el("input", { class: "entrada", id: "ft-nome", name: "nome", maxlength: 255, autocomplete: "off", placeholder: "Ex.: Mercado do mês" });
  nome.value = transacao?.nome ?? "";

  const chipsQuando = el("div", { class: "ft-chips", role: "group", "aria-label": "Data" });
  const dataOutra = el("input", { type: "date", class: "entrada ft-data", id: "ft-data", name: "data", "aria-label": "Escolher data", max: chaveDoDia(somarDias(hojeLocal, 366)) });
  dataOutra.value = estado.outraData;
  const erroData = el("p", { class: "campo-erro", id: "ft-data-erro" });
  dataOutra.setAttribute("aria-describedby", "ft-data-erro");

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
        erroValor,
      ),
      el("div", { class: "ft-secao campo" }, el("label", { class: "ft-rotulo", for: "ft-nome", texto: "Descrição" }), nome),
      el("div", { class: "ft-secao" }, el("h3", { texto: "Quando" }), chipsQuando, dataOutra, erroData),
      el(
        "div",
        { class: "ft-secao" },
        el("h3", { id: "ft-titulo-categoria", texto: "Categoria" }),
        seletor.bloco,
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

  function mudarTipo(tipo) {
    estado.tipo = tipo;
    dialogo.dataset.tipo = tipo;
    botoesTipo.forEach((b) => b.setAttribute("aria-pressed", String(b.classList.contains(tipo))));
    salvar.textContent = editando ? "Salvar alterações" : tipo === "despesa" ? "Salvar gasto" : "Salvar ganho";
    seletor.definirTipo(tipo);
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

  const inicial = () => JSON.stringify([estado.tipo, estado.centavos, estado.quando, dataOutra.value, seletor.valor(), estado.forma, nome.value, descricao.value]);
  const snapshot = inicial();
  const alterado = () => inicial() !== snapshot;

  async function pedirFechamento() {
    if (!alterado()) return true;
    return confirmar({
      titulo: editando ? "Descartar as alterações?" : "Descartar esta transação?",
      texto: editando ? "O que você mudou nesta transação vai se perder." : "O que você preencheu ainda não foi salvo.",
      confirmar: "Descartar",
      cancelar: "Continuar editando",
      perigo: true,
    });
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
  fechar.addEventListener("click", async () => {
    if (await pedirFechamento()) dialogo.close();
  });
  dialogo.addEventListener("cancel", async (evento) => {
    evento.preventDefault();
    if (await pedirFechamento()) dialogo.close();
  });
  dialogo.pedirFechamento = pedirFechamento;
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
      id_categoria: seletor.valor(),
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

  await seletor.carregar(fuso);
  agendarImpacto();
  return dialogo;
}
