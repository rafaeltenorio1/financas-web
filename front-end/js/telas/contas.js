import { api, ErroApi } from "../api.js";
import { el, icone, mensagem, ocupado } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { carregarCategorias, categoria } from "../categorias.js";
import { chaveDoDia, chaveDoMes, compararMeses, diaNoFuso, diasEntre, diasNoMes, hoje, inicioDoMes, instanteLocal, lerChaveDoDia, somarMeses } from "../datas.js";
import { moeda } from "../formatos.js";
import { iconeDaTransacao } from "../painel/componentes.js";
import { avisar } from "../avisos.js";
import { confirmar } from "../confirmar.js";
import { animacoesLigadas, recolher } from "../movimento.js";
import { abrirFormularioConta, FORMAS } from "../conta-form.js";
import { esquecerCachesDoFormulario } from "../transacao-form.js";

const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
const PERIODO_TEXTO = { mensal: "todo mês", semanal: "toda semana", anual: "todo ano" };
const nomeDoMes = new Intl.DateTimeFormat("pt-BR", { month: "long", timeZone: "UTC" });
const dataComAno = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const diaLongo = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });

const paraData = (chave) => {
  const { ano, mes, dia } = lerChaveDoDia(chave);
  return new Date(Date.UTC(ano, mes - 1, dia));
};
const deData = (d) => chaveDoDia({ ano: d.getUTCFullYear(), mes: d.getUTCMonth() + 1, dia: d.getUTCDate() });

function somarMesesComDia(chave, meses, diaOriginal) {
  const { ano, mes } = lerChaveDoDia(chave);
  const alvo = somarMeses({ ano, mes }, meses);
  return chaveDoDia({ ...alvo, dia: Math.min(diaOriginal, diasNoMes(alvo)) });
}

function proximaData(chave, conta) {
  if (conta.periodicidade === "semanal") {
    const d = paraData(chave);
    d.setUTCDate(d.getUTCDate() + 7);
    return deData(d);
  }
  const diaOriginal = lerChaveDoDia(conta.data_inicio).dia;
  return somarMesesComDia(chave, conta.periodicidade === "anual" ? 12 : 1, diaOriginal);
}

function vencimentosNoPeriodo(conta, inicio, fim) {
  const lista = [];
  let atual = conta.proximo_vencimento;
  for (let passos = 0; atual <= fim && passos < 400; passos += 1) {
    if (conta.data_fim && atual > conta.data_fim) break;
    if (atual >= inicio) lista.push(atual);
    atual = proximaData(atual, conta);
  }
  return lista;
}

function textoQuando(dias) {
  if (dias < 0) return [`atrasada há ${-dias} ${dias === -1 ? "dia" : "dias"}`, "atrasada"];
  if (dias === 0) return ["vence hoje", "perto"];
  if (dias === 1) return ["vence amanhã", "perto"];
  return [`vence em ${dias} dias`, dias <= 7 ? "perto" : ""];
}

function iconeDaConta(conta) {
  return iconeDaTransacao({ nome: conta.nome, id_categoria: conta.id_categoria, icone: conta.icone });
}

export async function montar(raiz) {
  const fuso = usuarioAtual().fuso;
  const hojeLocal = hoje(fuso);
  const hojeChave = chaveDoDia(hojeLocal);
  const mesAtual = { ano: hojeLocal.ano, mes: hojeLocal.mes };
  let mesCalendario = mesAtual;
  let diaEscolhido = null;
  let contas = [];
  let pagas = [];
  let pagarAberto = null;
  let aberta = null;

  const anuncio = el("p", { class: "sr", "aria-live": "polite" });
  const nova = el("button", { type: "button", class: "btn btn-primario" }, icone("mais", "ic-sm"), "Nova conta");
  const vistaLista = el("button", { type: "button", "aria-pressed": "true", texto: "Lista" });
  const vistaCalendario = el("button", { type: "button", "aria-pressed": "false", texto: "Calendário" });
  const lista = el("section", { class: "ct-lista", "aria-label": "Contas por prazo" });
  const resumo = el("dl", { class: "ct-resumo" });
  const tituloCal = el("h2", { id: "ct-titulo-cal" });
  const calAnterior = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Mês anterior" }, icone("anterior", "ic-sm"));
  const calProximo = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Próximo mês" }, icone("proximo", "ic-sm"));
  const dias = el("div", { class: "ct-dias" });
  const doDia = el("div", { class: "ct-do-dia", "aria-live": "polite" });
  const legenda = el("div", { class: "ct-legenda", "aria-hidden": "true" });
  for (const [cor, texto] of [["var(--despesa)", "atrasada"], ["var(--aviso)", "a pagar"], ["var(--texto-suave)", "paga"], ["var(--receita)", "a receber"]]) {
    const ponto = el("i");
    ponto.style.background = cor;
    legenda.append(el("span", {}, ponto, texto));
  }
  const lado = el(
    "aside",
    { class: "ct-lado", "aria-label": "Calendário das contas" },
    resumo,
    el(
      "section",
      { class: "ct-cal", "aria-labelledby": "ct-titulo-cal" },
      el("div", { class: "ct-cal-cab" }, calAnterior, tituloCal, calProximo),
      el("div", { class: "ct-semana", "aria-hidden": "true" }, SEMANA.map((d) => el("span", { texto: d }))),
      dias,
      legenda,
      doDia,
    ),
  );
  const grade = el("div", { class: "ct-grade" }, lista, lado);
  raiz.append(
    el("header", { class: "ct-cab" }, el("h1", { texto: "Contas" }), nova),
    el("div", { class: "ct-vista", role: "group", "aria-label": "Como ver as contas" }, vistaLista, vistaCalendario),
    anuncio,
    grade,
  );

  function escolherVista(calendario) {
    grade.classList.toggle("mostrar-calendario", calendario);
    vistaLista.setAttribute("aria-pressed", String(!calendario));
    vistaCalendario.setAttribute("aria-pressed", String(calendario));
  }
  vistaLista.addEventListener("click", () => escolherVista(false));
  vistaCalendario.addEventListener("click", () => escolherVista(true));

  function focarLinha(id) {
    grade.querySelector(`[data-conta="${CSS.escape(id)}"] .ct-abrir`)?.focus();
  }

  function alternarDetalhe(conta) {
    aberta = aberta === conta.id_conta_recorrente ? null : conta.id_conta_recorrente;
    if (aberta) pagarAberto = null;
    desenharLista();
    focarLinha(conta.id_conta_recorrente);
  }

  function fecharDetalhe(devolverFoco) {
    if (!aberta) return;
    const id = aberta;
    aberta = null;
    desenharLista();
    if (devolverFoco) focarLinha(id);
  }

  function detalheDaConta(conta) {
    const acao = (rotulo, simbolo, executar, classe = "btn-secundario") => {
      const botao = el("button", { type: "button", class: `btn ${classe}` }, icone(simbolo, "ic-sm"), rotulo);
      botao.addEventListener("click", executar);
      return botao;
    };
    const botoes = [];
    if (conta.ativa) {
      botoes.push(acao(conta.tipo === "receita" ? "Recebi" : "Pagar", "sucesso", () => abrirPagar(conta), "btn-primario so-celular"));
      botoes.push(acao("Pular este vencimento", "proximo", () => pular(conta)));
    }
    botoes.push(acao("Editar", "ajustes", () => abrirFormularioConta({ conta, aoSalvar: () => carregar() })));
    botoes.push(acao(conta.ativa ? "Pausar" : "Reativar", conta.ativa ? "cadeado" : "sucesso", () => alternarAtiva(conta)));
    botoes.push(acao("Apagar", "fechar", () => apagar(conta), "btn-secundario ct-perigo"));
    const periodo = PERIODO_TEXTO[conta.periodicidade];
    const itens = [
      ["Categoria", categoria(conta.id_categoria)?.nome ?? "Sem categoria"],
      ["Como costuma pagar", FORMAS.find(([valor]) => valor === conta.forma_pagamento)?.[1] ?? "Não informado"],
      ["Repete", periodo.charAt(0).toUpperCase() + periodo.slice(1)],
      ["Termina", conta.data_fim ? dataComAno.format(paraData(conta.data_fim)) : "Sem data para acabar"],
      ["Lembrete por e-mail", conta.avisar ? "Ligado" : "Desligado"],
    ];
    const dl = el("dl", {}, itens.map(([rotulo, valor]) => el("div", {}, el("dt", { texto: rotulo }), el("dd", { texto: valor }))));
    if (conta.descricao) dl.append(el("div", { class: "inteiro" }, el("dt", { texto: "Observação" }), el("dd", { texto: conta.descricao })));
    return el(
      "div",
      { class: "ct-detalhe", id: `detalhe-${conta.id_conta_recorrente}`, role: "region", "aria-label": `Opções de ${conta.nome}` },
      dl,
      el("div", { class: "ct-detalhe-botoes" }, ...botoes),
    );
  }

  async function pular(conta) {
    try {
      const atualizada = await api.post(`/contas-recorrentes/${conta.id_conta_recorrente}/pular`);
      avisar(`Vencimento pulado. Próximo: ${atualizada.ativa ? dataCurta(atualizada.proximo_vencimento) : "nenhum, a conta terminou"}.`);
      carregar();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.message, { tipo: "erro" });
    }
  }

  function sino(conta) {
    const ligado = conta.avisar;
    const botao = el("button", { type: "button", class: "ct-sino", "aria-pressed": String(ligado), title: ligado ? "Lembrete por e-mail ligado" : "Lembrete por e-mail desligado" }, icone(ligado ? "sino-ativo" : "sino-off"));
    botao.setAttribute("aria-label", `Lembrete por e-mail de ${conta.nome}`);
    botao.addEventListener("click", () => alternarLembrete(conta));
    return botao;
  }

  async function alternarLembrete(conta) {
    const ligar = !conta.avisar;
    if (!ligar) {
      const sim = await confirmar({
        titulo: "Desligar os lembretes?",
        texto: `Você deixa de receber e-mails antes do vencimento de “${conta.nome}”. Dá para ligar de novo tocando no sino.`,
        confirmar: "Desligar lembretes",
        cancelar: "Manter ligados",
        perigo: true,
      });
      if (!sim) return;
    }
    try {
      await api.patch(`/contas-recorrentes/${conta.id_conta_recorrente}`, { avisar: ligar });
      conta.avisar = ligar;
      avisar(ligar ? `Lembretes de ${conta.nome} ligados.` : `Lembretes de ${conta.nome} desligados.`);
      desenharLista();
      grade.querySelector(`[data-conta="${CSS.escape(conta.id_conta_recorrente)}"] .ct-sino`)?.focus();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.message, { tipo: "erro" });
    }
  }

  async function alternarAtiva(conta) {
    try {
      await api.patch(`/contas-recorrentes/${conta.id_conta_recorrente}`, { ativa: !conta.ativa });
      avisar(conta.ativa ? `${conta.nome} pausada. Ela não gera lembretes até ser reativada.` : `${conta.nome} reativada.`);
      carregar();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.message, { tipo: "erro" });
    }
  }

  async function apagar(conta) {
    const sim = await confirmar({
      titulo: `Apagar a conta “${conta.nome}”?`,
      texto: "As transações que você já pagou continuam no histórico.",
      confirmar: "Apagar conta",
      perigo: true,
    });
    if (!sim) return;
    try {
      await api.delete(`/contas-recorrentes/${conta.id_conta_recorrente}`);
      await recolher(grade.querySelector(`[data-conta="${CSS.escape(conta.id_conta_recorrente)}"]`));
      avisar(`Conta ${conta.nome} apagada.`);
      carregar();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      avisar(erro.message, { tipo: "erro" });
    }
  }

  function dataCurta(chave) {
    const { mes, dia } = lerChaveDoDia(chave);
    return `${dia} ${MESES_CURTOS[mes - 1]}`;
  }

  function abrirPagar(conta) {
    pagarAberto = pagarAberto === conta.id_conta_recorrente ? null : conta.id_conta_recorrente;
    if (pagarAberto) aberta = null;
    desenharLista();
    if (pagarAberto) grade.querySelector(`#pagar-${conta.id_conta_recorrente} input`)?.focus();
  }

  function formularioPagar(conta) {
    const recebimento = conta.tipo === "receita";
    let centavos = String(Math.round(Number(conta.valor) * 100));
    const valor = el("input", { class: "entrada", inputmode: "numeric", autocomplete: "off", value: moeda(Number(centavos) / 100) });
    valor.addEventListener("input", () => {
      centavos = valor.value.replace(/\D/g, "").replace(/^0+/, "").slice(0, 11);
      valor.value = moeda(Number(centavos || "0") / 100);
    });
    const data = el("input", { type: "date", class: "entrada", value: hojeChave, max: hojeChave });
    const forma = el("select", { class: "entrada" }, el("option", { value: "", texto: "Não informar" }), FORMAS.map(([v, r]) => el("option", { value: v, selected: v === conta.forma_pagamento, texto: r })));
    const botaoConfirmar = el("button", { type: "submit", class: "btn btn-primario", texto: recebimento ? "Confirmar recebimento" : "Confirmar pagamento" });
    const cancelar = el("button", { type: "button", class: "btn btn-secundario", texto: "Cancelar" });
    const aviso = el("div", { class: "mensagem", role: "alert" });
    cancelar.addEventListener("click", () => abrirPagar(conta));
    const form = el(
      "form",
      { class: "ct-pagar", id: `pagar-${conta.id_conta_recorrente}`, "aria-label": `${recebimento ? "Receber" : "Pagar"} ${conta.nome}` },
      el("label", {}, recebimento ? "Valor recebido" : "Valor pago", valor),
      el("label", {}, "Data", data),
      el("label", {}, "Forma", forma),
      el("div", { class: "ct-pagar-botoes" }, cancelar, botaoConfirmar),
      aviso,
    );
    form.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      mensagem(aviso, "erro", "");
      if (!Number(centavos)) {
        mensagem(aviso, "erro", "Informe um valor maior que zero.");
        return valor.focus();
      }
      const dia = lerChaveDoDia(data.value);
      if (!dia) {
        mensagem(aviso, "erro", "Escolha a data.");
        return data.focus();
      }
      const dataHora = data.value === hojeChave ? new Date().toISOString() : instanteLocal({ ...dia, hora: 12 }, fuso).toISOString();
      ocupado(botaoConfirmar, true, "Salvando…");
      try {
        const resultado = await api.post(`/contas-recorrentes/${conta.id_conta_recorrente}/pagar`, {
          valor: (Number(centavos) / 100).toFixed(2),
          data_hora: dataHora,
          forma_pagamento: forma.value || null,
        });
        esquecerCachesDoFormulario();
        ocupado(botaoConfirmar, false);
        botaoConfirmar.replaceChildren(icone("sucesso", "ic-sm"), recebimento ? "Recebido" : "Pago");
        botaoConfirmar.classList.add("feito");
        if (animacoesLigadas()) await new Promise((resolver) => setTimeout(resolver, 450));
        await recolher(form.closest(".ct-conta"));
        pagarAberto = null;
        const proximo = resultado.conta.ativa ? ` Próximo vencimento: ${dataCurta(resultado.conta.proximo_vencimento)}.` : " Era o último vencimento.";
        avisar(`${conta.nome}: ${moeda(resultado.transacao.valor)} ${recebimento ? "recebido" : "pago"}.${proximo}`);
        carregar();
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        ocupado(botaoConfirmar, false);
        mensagem(aviso, "erro", erro.message);
      }
    });
    return form;
  }

  function linha(conta) {
    const { dia, mes } = lerChaveDoDia(conta.proximo_vencimento);
    const dias = diasEntre(hojeChave, conta.proximo_vencimento);
    const [quando, classe] = conta.ativa ? textoQuando(dias) : ["pausada", ""];
    const cat = categoria(conta.id_categoria);
    const meta = el("span", { class: "ct-meta" }, el("span", { class: classe, texto: quando }), `, ${PERIODO_TEXTO[conta.periodicidade]}`);
    if (cat) meta.append(`, ${cat.nome}`);
    const direita = el("div", { class: "ct-direita" }, el("span", { class: `ct-valor${conta.tipo === "receita" ? " receita" : ""}`, texto: moeda(conta.valor) }));
    if (conta.ativa) direita.append(sino(conta));
    if (conta.ativa) {
      const pagar = el("button", { type: "button", class: "btn btn-secundario btn-pagar", "aria-expanded": String(pagarAberto === conta.id_conta_recorrente), texto: conta.tipo === "receita" ? "Recebi" : "Pagar" });
      pagar.setAttribute("aria-label", `${conta.tipo === "receita" ? "Registrar recebimento de" : "Pagar"} ${conta.nome}`);
      pagar.addEventListener("click", () => abrirPagar(conta));
      direita.append(pagar);
    }
    const estaAberta = aberta === conta.id_conta_recorrente;
    const abrir = el(
      "button",
      { type: "button", class: "ct-abrir", "aria-expanded": String(estaAberta), "aria-controls": estaAberta ? `detalhe-${conta.id_conta_recorrente}` : null },
      el("span", { class: "ct-data", "aria-hidden": "true" }, el("b", { texto: dia }), el("small", { texto: MESES_CURTOS[mes - 1] })),
      el("span", { class: "sr", texto: `Vencimento em ${dia} de ${nomeDoMes.format(new Date(Date.UTC(2000, mes - 1, 1)))}.` }),
      iconeDaConta(conta),
      el("span", { class: "ct-info" }, el("span", { class: "ct-nome", texto: conta.nome }), meta),
    );
    abrir.addEventListener("click", () => alternarDetalhe(conta));
    const item = el(
      "div",
      { class: "ct-conta", "data-conta": conta.id_conta_recorrente },
      abrir,
      direita,
    );
    item.classList.toggle("aberta", estaAberta);
    if (estaAberta) item.append(detalheDaConta(conta));
    if (pagarAberto === conta.id_conta_recorrente) item.append(formularioPagar(conta));
    return item;
  }

  function desenharLista() {
    lista.replaceChildren();
    if (!contas.length) {
      const botao = el("button", { type: "button", class: "btn btn-primario", texto: "Cadastrar a primeira conta" });
      botao.addEventListener("click", () => nova.click());
      lista.append(el("div", { class: "ct-vazio" }, el("strong", { texto: "Você ainda não tem contas recorrentes." }), "Cadastre aluguel, internet, assinaturas e o Finanças avisa antes de vencer.", el("br"), botao));
      return;
    }
    const ativasDespesa = contas.filter((c) => c.ativa && c.tipo === "despesa");
    const fimProximoMes = chaveDoDia({ ...somarMeses(mesAtual, 1), dia: diasNoMes(somarMeses(mesAtual, 1)) });
    const grupos = [
      ["Atrasadas", ativasDespesa.filter((c) => c.proximo_vencimento < hojeChave), "atraso"],
      ["Nos próximos 7 dias", ativasDespesa.filter((c) => c.proximo_vencimento >= hojeChave && diasEntre(hojeChave, c.proximo_vencimento) <= 7)],
      ["Ainda este mês e o próximo", ativasDespesa.filter((c) => diasEntre(hojeChave, c.proximo_vencimento) > 7 && c.proximo_vencimento <= fimProximoMes)],
      ["Mais adiante", ativasDespesa.filter((c) => c.proximo_vencimento > fimProximoMes)],
      ["A receber", contas.filter((c) => c.ativa && c.tipo === "receita")],
    ];
    for (const [titulo, itens, classe] of grupos) {
      if (!itens.length) continue;
      itens.sort((a, b) => a.proximo_vencimento.localeCompare(b.proximo_vencimento));
      lista.append(el("section", { class: `ct-grupo ${classe ?? ""}`, "aria-label": titulo }, el("h2", {}, titulo, el("span", { class: "ct-contagem", texto: itens.length })), el("div", { class: "ct-caixa" }, itens.map(linha))));
    }
    const pausadas = contas.filter((c) => !c.ativa);
    if (pausadas.length) {
      lista.append(el("details", { class: "ct-grupo ct-pausadas" }, el("summary", { texto: `Pausadas (${pausadas.length})` }), el("div", { class: "ct-caixa" }, pausadas.map(linha))));
    }
  }

  function eventosDoMes() {
    const inicio = chaveDoDia({ ...mesCalendario, dia: 1 });
    const fim = chaveDoDia({ ...mesCalendario, dia: diasNoMes(mesCalendario) });
    const eventos = [];
    for (const conta of contas.filter((c) => c.ativa)) {
      for (const dia of vencimentosNoPeriodo(conta, inicio, fim)) {
        const situacao = conta.tipo === "receita" ? "receber" : dia < hojeChave ? "atrasada" : "pagar";
        eventos.push({ dia, nome: conta.nome, valor: Number(conta.valor), situacao, conta, pagavel: dia === conta.proximo_vencimento });
      }
      if (conta.proximo_vencimento < inicio && conta.tipo === "despesa" && compararMeses(mesCalendario, mesAtual) === 0) {
        eventos.push({ dia: conta.proximo_vencimento, nome: conta.nome, valor: Number(conta.valor), situacao: "atrasada", conta, pagavel: true, deOutroMes: true });
      }
    }
    for (const t of pagas) {
      const dia = chaveDoDia(diaNoFuso(t.data_hora, fuso));
      if (dia >= inicio && dia <= fim) eventos.push({ dia, nome: t.nome || "Conta", valor: Number(t.valor), situacao: t.tipo === "receita" ? "recebida" : "paga" });
    }
    return { eventos, inicio, fim };
  }

  function desenharCalendario() {
    tituloCal.textContent = `${nomeDoMes.format(new Date(Date.UTC(mesCalendario.ano, mesCalendario.mes - 1, 15)))} de ${mesCalendario.ano}`;
    const { eventos } = eventosDoMes();
    const doMes = eventos.filter((e) => !e.deOutroMes);
    const faltaPagar = eventos.filter((e) => e.situacao === "pagar" || e.situacao === "atrasada").reduce((s, e) => s + e.valor, 0);
    const pago = doMes.filter((e) => e.situacao === "paga").reduce((s, e) => s + e.valor, 0);
    const nome = nomeDoMes.format(new Date(Date.UTC(mesCalendario.ano, mesCalendario.mes - 1, 15)));
    resumo.replaceChildren(
      el("div", {}, el("dt", { texto: `Falta pagar em ${nome}` }), el("dd", { class: faltaPagar ? "perto" : "", texto: moeda(faltaPagar) })),
      el("div", {}, el("dt", { texto: `Pago em ${nome}` }), el("dd", { texto: moeda(pago) })),
    );
    dias.replaceChildren();
    const primeiro = new Date(Date.UTC(mesCalendario.ano, mesCalendario.mes - 1, 1)).getUTCDay();
    for (let i = 0; i < primeiro; i += 1) dias.append(el("span", { class: "ct-dia vazio", "aria-hidden": "true" }));
    for (let d = 1; d <= diasNoMes(mesCalendario); d += 1) {
      const chave = chaveDoDia({ ...mesCalendario, dia: d });
      const doDiaEventos = doMes.filter((e) => e.dia === chave);
      const classes = `ct-dia${chave === hojeChave ? " hoje" : ""}`;
      if (!doDiaEventos.length) {
        dias.append(el("span", { class: classes, texto: d }));
        continue;
      }
      const resumoDia = doDiaEventos.map((e) => `${e.nome}, ${{ pagar: "a pagar", atrasada: "atrasada", paga: "paga", recebida: "recebida", receber: "a receber" }[e.situacao]}`).join("; ");
      const botao = el(
        "button",
        { type: "button", class: classes, "aria-pressed": String(diaEscolhido === chave), "aria-label": `${d}: ${resumoDia}` },
        el("span", { texto: d }),
        el("span", { class: "ct-pontos", "aria-hidden": "true" }, doDiaEventos.slice(0, 4).map((e) => el("i", { class: { pagar: "", atrasada: "atrasada", paga: "paga", recebida: "paga", receber: "receber" }[e.situacao] }))),
      );
      botao.addEventListener("click", () => {
        diaEscolhido = diaEscolhido === chave ? null : chave;
        desenharCalendario();
        dias.querySelector(`[aria-pressed="true"]`)?.focus();
      });
      dias.append(botao);
    }
    doDia.replaceChildren();
    if (diaEscolhido) {
      const itens = doMes.filter((e) => e.dia === diaEscolhido);
      doDia.append(el("h3", { texto: diaLongo.format(paraData(diaEscolhido)) }));
      for (const e of itens) {
        const linhaDia = el("div", { class: "ct-item-dia" }, el("span", { class: e.situacao === "paga" || e.situacao === "recebida" ? "paga" : "", texto: e.nome }));
        if (e.pagavel) {
          const botao = el("button", { type: "button", class: "btn btn-secundario", texto: `${e.conta.tipo === "receita" ? "Recebi" : "Pagar"} ${moeda(e.valor)}` });
          botao.addEventListener("click", () => {
            escolherVista(false);
            if (pagarAberto !== e.conta.id_conta_recorrente) abrirPagar(e.conta);
            grade.querySelector(`#pagar-${e.conta.id_conta_recorrente}`)?.scrollIntoView({ block: "center" });
          });
          linhaDia.append(botao);
        } else {
          linhaDia.append(el("span", { class: "estado", texto: `${moeda(e.valor)}${e.situacao === "paga" ? ", paga" : e.situacao === "recebida" ? ", recebida" : ", prevista"}` }));
        }
        doDia.append(linhaDia);
      }
    }
  }

  async function carregarPagasDoMes() {
    const inicio = inicioDoMes(mesCalendario, fuso).toISOString();
    const fim = inicioDoMes(somarMeses(mesCalendario, 1), fuso).toISOString();
    const todas = [];
    for (let offset = 0; offset < 2000; offset += 100) {
      const pagina = await api.get(`/transacoes?${new URLSearchParams({ data_inicio: inicio, data_fim: fim, limit: 100, offset })}`);
      todas.push(...pagina);
      if (pagina.length < 100) break;
    }
    pagas = todas.filter((t) => t.id_conta_recorrente);
  }

  async function carregar() {
    try {
      const [lista1] = await Promise.all([api.get("/contas-recorrentes?limit=100"), carregarCategorias(), carregarPagasDoMes()]);
      contas = lista1;
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      const tentar = el("button", { type: "button", class: "btn btn-secundario", texto: "Tentar de novo" });
      tentar.addEventListener("click", carregar);
      lista.replaceChildren(el("div", { class: "ct-vazio", role: "alert" }, el("strong", { texto: "Não foi possível carregar as contas." }), erro.message, el("br"), tentar));
      return;
    }
    desenharLista();
    desenharCalendario();
    const atrasadas = contas.filter((c) => c.ativa && c.tipo === "despesa" && c.proximo_vencimento < hojeChave).length;
    anuncio.textContent = `${contas.length} contas recorrentes${atrasadas ? `, ${atrasadas} atrasadas` : ""}.`;
  }

  async function mudarMes(passo) {
    mesCalendario = somarMeses(mesCalendario, passo);
    diaEscolhido = null;
    try {
      await carregarPagasDoMes();
    } catch {
      pagas = [];
    }
    desenharCalendario();
  }
  calAnterior.addEventListener("click", () => mudarMes(-1));
  calProximo.addEventListener("click", () => mudarMes(1));
  nova.addEventListener("click", () => abrirFormularioConta({ aoSalvar: () => carregar() }));

  function aoClicarFora(evento) {
    if (!aberta || document.querySelector("dialog[open]")) return;
    if (evento.target.closest(".ct-conta, .aviso-flutuante")) return;
    fecharDetalhe(false);
  }
  function aoTeclar(evento) {
    if (evento.key === "Escape" && aberta && !document.querySelector("dialog[open]")) fecharDetalhe(true);
  }
  document.addEventListener("pointerdown", aoClicarFora, true);
  document.addEventListener("keydown", aoTeclar);

  lista.append(el("div", { class: "ct-vazio", "aria-busy": "true" }, "Carregando…"));
  await carregar();

  return () => {
    document.removeEventListener("pointerdown", aoClicarFora, true);
    document.removeEventListener("keydown", aoTeclar);
  };
}
