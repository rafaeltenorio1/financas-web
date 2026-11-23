import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { usuarioAtual } from "./sessao.js";
import { chaveDoDia, hoje } from "./datas.js";
import { moeda } from "./formatos.js";
import { avisar } from "./avisos.js";
import { criarSeletorDeCategorias } from "./seletor-categorias.js";
import { esquecerCachesDoFormulario } from "./transacao-form.js";

export const FORMAS = [
  ["pix", "Pix"],
  ["cartao de credito", "Cartão de crédito"],
  ["cartao de debito", "Cartão de débito"],
  ["boleto", "Boleto"],
  ["dinheiro", "Dinheiro"],
];
export const PERIODICIDADES = [
  ["mensal", "Todo mês"],
  ["semanal", "Toda semana"],
  ["anual", "Todo ano"],
];

function formatarCentavos(digitos) {
  return moeda(Number(digitos || "0") / 100);
}

export async function abrirFormularioConta({ conta = null, aoSalvar } = {}) {
  const fuso = usuarioAtual()?.fuso ?? "America/Sao_Paulo";
  const editando = conta !== null;
  const origemDoFoco = document.activeElement;
  const estado = {
    tipo: conta?.tipo ?? "despesa",
    centavos: editando ? String(Math.round(Number(conta.valor) * 100)) : "",
    periodicidade: conta?.periodicidade ?? "mensal",
    forma: conta?.forma_pagamento ?? null,
  };
  const seletor = criarSeletorDeCategorias({ prefixo: "fc", tipo: estado.tipo, selecionada: conta?.id_categoria ?? null, rotuladoPor: "fc-titulo-categoria" });

  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
  const botoesTipo = [
    ["despesa", "Conta a pagar", "sai"],
    ["receita", "A receber", "entra"],
  ].map(([tipo, rotulo, simbolo]) => {
    const botao = el("button", { type: "button", class: tipo, "aria-pressed": "false" }, icone(simbolo, "ic-sm"), rotulo);
    botao.addEventListener("click", () => mudarTipo(tipo));
    return botao;
  });
  const erroValor = el("p", { class: "campo-erro", id: "fc-valor-erro" });
  const valor = el("input", { id: "fc-valor", name: "valor", inputmode: "numeric", autocomplete: "off", "aria-describedby": "fc-valor-ajuda fc-valor-erro", value: formatarCentavos(estado.centavos) });
  const erroNome = el("p", { class: "campo-erro", id: "fc-nome-erro" });
  const nome = el("input", { class: "entrada", id: "fc-nome", name: "nome", maxlength: 255, autocomplete: "off", placeholder: "Ex.: Aluguel, Internet, Netflix", "aria-describedby": "fc-nome-erro" });
  nome.value = conta?.nome ?? "";

  const chipsPeriodo = el("div", { class: "ft-chips", role: "group", "aria-labelledby": "fc-titulo-periodo" });
  const notaPeriodo = editando ? el("p", { class: "campo-ajuda", texto: "Para mudar a frequência, crie uma conta nova e apague esta." }) : null;
  const rotuloData = editando ? "Próximo vencimento" : "Primeiro vencimento";
  const data = el("input", { type: "date", class: "entrada ft-data", id: "fc-data", name: "vencimento", "aria-describedby": "fc-data-erro" });
  data.value = editando ? conta.proximo_vencimento : chaveDoDia(hoje(fuso));
  const erroData = el("p", { class: "campo-erro", id: "fc-data-erro" });
  const temFim = el("input", { type: "checkbox", id: "fc-tem-fim", name: "tem-fim" });
  const fim = el("input", { type: "date", class: "entrada ft-data", id: "fc-fim", name: "fim", "aria-label": "Último vencimento", "aria-describedby": "fc-fim-erro" });
  const erroFim = el("p", { class: "campo-erro", id: "fc-fim-erro" });
  if (conta?.data_fim) {
    temFim.checked = true;
    fim.value = conta.data_fim;
  }
  fim.hidden = !temFim.checked;
  const avisarCaixa = el("input", { type: "checkbox", id: "fc-avisar", name: "avisar" });
  avisarCaixa.checked = conta?.avisar ?? true;
  const chipsForma = el("div", { class: "ft-chips", role: "group", "aria-labelledby": "fc-titulo-forma" });
  const descricao = el("textarea", { class: "entrada", id: "fc-descricao", name: "descricao", maxlength: 1000, "aria-label": "Observação" });
  descricao.value = conta?.descricao ?? "";
  const observacao = el("details", {}, el("summary", { texto: "Adicionar observação" }), descricao);
  if (descricao.value) observacao.open = true;

  const avisoErro = el("div", { class: "mensagem", role: "alert" });
  const salvar = el("button", { type: "submit", class: "btn btn-primario", texto: editando ? "Salvar alterações" : "Salvar conta" });
  const formulario = el(
    "form",
    { novalidate: true },
    el(
      "div",
      { class: "ft-corpo" },
      el("div", { class: "ft-topo" }, fechar, el("h2", { id: "fc-titulo", texto: editando ? "Editar conta" : "Nova conta" })),
      el(
        "div",
        { class: "ft-valor" },
        el("div", { class: "ft-tipo", role: "group", "aria-label": "Tipo" }, ...botoesTipo),
        el("label", { for: "fc-valor", texto: "Valor" }),
        valor,
        el("p", { class: "campo-ajuda", id: "fc-valor-ajuda", texto: "Digite só os números: 4590 vira R$ 45,90." }),
        erroValor,
      ),
      el("div", { class: "ft-secao campo" }, el("label", { class: "ft-rotulo", for: "fc-nome", texto: "Nome" }), nome, erroNome),
      el("div", { class: "ft-secao" }, el("h3", { id: "fc-titulo-periodo", texto: "Repete" }), chipsPeriodo, notaPeriodo),
      el("div", { class: "ft-secao campo" }, el("label", { class: "ft-rotulo", for: "fc-data", texto: rotuloData }), data, erroData),
      el("div", { class: "ft-secao" }, el("label", { class: "marcar", for: "fc-tem-fim" }, temFim, "Tem data para acabar"), fim, erroFim),
      el("div", { class: "ft-secao" }, el("h3", { id: "fc-titulo-categoria", texto: "Categoria" }), seletor.bloco),
      el("div", { class: "ft-secao" }, el("h3", { id: "fc-titulo-forma", texto: "Como costuma pagar" }), chipsForma),
      el("div", { class: "ft-secao" }, el("label", { class: "marcar", for: "fc-avisar" }, avisarCaixa, "Me avisar por e-mail antes de vencer")),
      el("div", { class: "ft-secao" }, observacao),
    ),
    el("div", { class: "ft-rodape" }, avisoErro, salvar),
  );
  const dialogo = el("dialog", { class: "form-transacao", "aria-labelledby": "fc-titulo" }, formulario);

  function desenharPeriodos() {
    chipsPeriodo.replaceChildren();
    for (const [chave, rotulo] of PERIODICIDADES) {
      const chip = el("button", { type: "button", class: "ft-chip", "aria-pressed": String(estado.periodicidade === chave), disabled: editando, texto: rotulo });
      chip.addEventListener("click", () => {
        estado.periodicidade = chave;
        desenharPeriodos();
      });
      chipsPeriodo.append(chip);
    }
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
    seletor.definirTipo(tipo);
  }

  function marcar(campo, erro, texto) {
    erro.textContent = texto;
    if (texto) campo.setAttribute("aria-invalid", "true");
    else campo.removeAttribute("aria-invalid");
  }

  const retrato = () => JSON.stringify([estado.tipo, estado.centavos, estado.periodicidade, estado.forma, seletor.valor(), nome.value, data.value, temFim.checked, fim.value, avisarCaixa.checked, descricao.value]);
  const inicial = retrato();
  const podeFechar = () => retrato() === inicial || confirm(editando ? "Descartar as alterações desta conta?" : "Descartar esta conta sem salvar?");

  valor.addEventListener("input", () => {
    estado.centavos = valor.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 11);
    valor.value = formatarCentavos(estado.centavos);
    valor.setSelectionRange(valor.value.length, valor.value.length);
    marcar(valor, erroValor, "");
  });
  nome.addEventListener("input", () => marcar(nome, erroNome, ""));
  data.addEventListener("input", () => marcar(data, erroData, ""));
  fim.addEventListener("input", () => marcar(fim, erroFim, ""));
  temFim.addEventListener("change", () => {
    fim.hidden = !temFim.checked;
    if (temFim.checked) fim.focus();
    else marcar(fim, erroFim, "");
  });
  fechar.addEventListener("click", () => {
    if (podeFechar()) dialogo.close();
  });
  dialogo.addEventListener("cancel", (evento) => {
    if (!podeFechar()) evento.preventDefault();
  });
  dialogo.addEventListener("close", () => {
    dialogo.remove();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(avisoErro, "erro", "");
    const centavos = Number(estado.centavos || "0");
    marcar(valor, erroValor, centavos > 0 ? "" : "Informe um valor maior que zero.");
    marcar(nome, erroNome, nome.value.trim() ? "" : "Dê um nome para a conta.");
    marcar(data, erroData, data.value ? "" : "Escolha a data do vencimento.");
    marcar(fim, erroFim, temFim.checked && !fim.value ? "Escolha o último vencimento." : temFim.checked && fim.value < data.value ? "O fim não pode ser antes do vencimento." : "");
    const primeiro = [[valor, erroValor], [nome, erroNome], [data, erroData], [fim, erroFim]].find(([, e]) => e.textContent);
    if (primeiro) return primeiro[0].focus();

    const comum = {
      tipo: estado.tipo,
      nome: nome.value.trim(),
      valor: (centavos / 100).toFixed(2),
      id_categoria: seletor.valor(),
      forma_pagamento: estado.forma,
      data_fim: temFim.checked ? fim.value : null,
      avisar: avisarCaixa.checked,
      descricao: descricao.value.trim() || null,
    };
    const corpo = editando ? { ...comum, proximo_vencimento: data.value } : { ...comum, periodicidade: estado.periodicidade, data_inicio: data.value };
    ocupado(salvar, true, "Salvando…");
    try {
      const salva = editando ? await api.patch(`/contas-recorrentes/${conta.id_conta_recorrente}`, corpo) : await api.post("/contas-recorrentes", corpo);
      esquecerCachesDoFormulario();
      dialogo.close("salvo");
      avisar(editando ? `Conta ${salva.nome} atualizada.` : `Conta ${salva.nome} cadastrada.`);
      aoSalvar?.(salva);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.campos.valor) {
        marcar(valor, erroValor, "Confira o valor.");
        valor.focus();
      } else if (erro.campos.nome) {
        marcar(nome, erroNome, "Confira o nome.");
        nome.focus();
      } else {
        mensagem(avisoErro, "erro", erro.status === 422 && erro.message === "Confira os campos destacados." ? "Confira as datas: o fim não pode ser antes do vencimento." : erro.message);
      }
    } finally {
      if (dialogo.isConnected) ocupado(salvar, false);
    }
  });

  document.body.append(dialogo);
  mudarTipo(estado.tipo);
  desenharPeriodos();
  desenharFormas();
  dialogo.showModal();
  if (matchMedia("(min-width: 900px)").matches) (editando ? nome : valor).focus();
  await seletor.carregar(fuso);
  return dialogo;
}
