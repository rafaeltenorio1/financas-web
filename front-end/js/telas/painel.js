import { confirmar } from "../confirmar.js";
import { animarNumeros, entrarDoLado } from "../movimento.js";

let ultimoMesVisto = null;
import { el, icone, mensagem, ocupado } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { definirGuardaDeSaida } from "../rotas.js";
import { chaveDoMes, compararMeses, hoje, lerChaveDoMes, somarMeses } from "../datas.js";
import { mesAno } from "../formatos.js";
import { avisoDeContas, contextoDoMes } from "../painel/calculos.js";
import { DEPENDENCIAS, carregarFontes, fontesDosCartoes, periodoDoMes } from "../painel/dados.js";
import { lerPreferencias, salvarDepois, salvarPreferencias } from "../painel/preferencias.js";
import { erroDoCartao, esqueleto } from "../painel/componentes.js";
import { criarEdicao } from "../painel/edicao.js";
import saldo from "../painel/cartoes/saldo.js";
import transacoes from "../painel/cartoes/transacoes.js";
import { gastosPorCategoria, ganhosPorCategoria } from "../painel/cartoes/categorias.js";
import meses from "../painel/cartoes/meses.js";
import numeros from "../painel/cartoes/numeros.js";
import contas from "../painel/cartoes/contas.js";

const CARTOES = Object.fromEntries([saldo, transacoes, gastosPorCategoria, ganhosPorCategoria, meses, numeros, contas].map((c) => [c.id, c]));
const TITULOS = Object.fromEntries(Object.values(CARTOES).map((c) => [c.id, c.titulo]));
const listaPt = new Intl.ListFormat("pt-BR", { style: "long", type: "conjunction" });
const ESPACO = 18;
const LINHA = 4;

function navegacaoDoMes(mes, atual) {
  const anterior = somarMeses(mes, -1);
  const seguinte = somarMeses(mes, 1);
  const titulo = el("h1", { texto: mesAno(new Date(Date.UTC(mes.ano, mes.mes - 1, 15, 12)).toISOString()) });
  const voltar = el("a", { class: "painel-mes-seta", href: `#/?mes=${chaveDoMes(anterior)}`, "aria-label": "Mês anterior" }, icone("anterior"));
  const avancar = atual
    ? el("span", { class: "painel-mes-seta", "aria-disabled": "true", title: "Você já está no mês atual" }, icone("proximo"))
    : el("a", { class: "painel-mes-seta", href: `#/?mes=${chaveDoMes(seguinte)}`, "aria-label": "Próximo mês" }, icone("proximo"));
  return el("div", { class: "painel-mes" }, voltar, titulo, avancar);
}

function textoDoAviso(aviso) {
  if (aviso.atrasadas) {
    const n = aviso.atrasadas;
    return [`${n} ${n === 1 ? "conta está" : "contas estão"} em atraso`, true];
  }
  const nomes = aviso.contas.map((c) => c.nome);
  const exibidos = nomes.length > 3 ? [...nomes.slice(0, 2), `mais ${nomes.length - 2}`] : nomes;
  return [`${listaPt.format(exibidos)} ${nomes.length === 1 ? "vence" : "vencem"} nos próximos dias`, false];
}

export async function montar(raiz, { parametros }) {
  const usuario = usuarioAtual();
  const fuso = usuario.fuso;
  const hojeLocal = hoje(fuso);
  const mesAtual = { ano: hojeLocal.ano, mes: hojeLocal.mes };
  let mes = lerChaveDoMes(parametros.get("mes")) ?? mesAtual;
  if (compararMeses(mes, mesAtual) > 0) mes = mesAtual;

  let preferencias = lerPreferencias(usuario);
  const contexto = contextoDoMes(mes, hojeLocal);
  const contextoAtual = contextoDoMes(mesAtual, hojeLocal);
  const fontes = { periodo: periodoDoMes(mes, fuso), fuso };
  const controle = new AbortController();
  const dados = {};
  const erros = {};
  const carregadas = new Set();
  const limpezas = new Map();
  const secoes = new Map();
  const conteudos = new Map();

  const anuncio = el("p", { class: "sr", "aria-live": "polite" });
  const status = el("div", { class: "mensagem", role: "alert" });
  const avisoSlot = el("div");
  const grade = el("div", { class: "painel" });
  const direcaoDoMes = ultimoMesVisto ? Math.sign(compararMeses(mes, ultimoMesVisto)) : 0;
  ultimoMesVisto = mes;
  requestAnimationFrame(() => entrarDoLado(grade, direcaoDoMes));
  const adicionar = el("section", { class: "adicionar" });
  const botoes = el("div", { class: "painel-botoes" });
  const cabecalhoTela = el("header", { class: "painel-cab" }, navegacaoDoMes(mes, contexto.atual), botoes);
  raiz.append(
    cabecalhoTela,
    avisoSlot,
    el("div", { class: "painel-status" }, status),
    anuncio,
    grade,
    adicionar,
  );
  const anunciar = (texto) => {
    anuncio.textContent = "";
    requestAnimationFrame(() => (anuncio.textContent = texto));
  };

  const desktop = matchMedia("(min-width: 900px)");
  const alturaEmLinhas = (altura) => Math.ceil((altura + ESPACO) / LINHA);
  function ajustarAltura(secao) {
    if (!desktop.matches || secao.classList.contains("arrastando")) {
      if (!desktop.matches) secao.style.gridRowEnd = "";
      return;
    }
    secao.style.gridRowEnd = `span ${alturaEmLinhas(secao.getBoundingClientRect().height)}`;
  }
  const observador = new ResizeObserver((entradas) => {
    for (const { target } of entradas) ajustarAltura(target);
  });
  const aoMudarTela = () => secoes.forEach(ajustarAltura);
  desktop.addEventListener("change", aoMudarTela);

  function desmontarCartao(id) {
    for (const limpar of limpezas.get(id) ?? []) limpar();
    limpezas.set(id, []);
  }

  function preencher(id) {
    const conteudo = conteudos.get(id);
    const definicao = CARTOES[id];
    desmontarCartao(id);
    conteudo.replaceChildren();
    secoes.get(id).removeAttribute("aria-busy");
    if (DEPENDENCIAS[id].some((fonte) => erros[fonte])) {
      conteudo.append(erroDoCartao(definicao.titulo, () => recarregar(id)));
      return;
    }
    definicao.montar(conteudo, {
      dados,
      mes,
      contexto,
      contextoAtual,
      preferencias,
      alterarPreferencias,
      salvarAgora,
      aoDesmontar: (limpar) => limpezas.get(id).push(limpar),
    });
    animarNumeros(conteudo);
  }

  async function recarregar(id) {
    const conteudo = conteudos.get(id);
    conteudo.replaceChildren(esqueleto());
    secoes.get(id).setAttribute("aria-busy", "true");
    const pendentes = DEPENDENCIAS[id].filter((fonte) => erros[fonte] || !carregadas.has(fonte));
    const resultado = await carregarFontes(pendentes, fontes, controle.signal);
    if (controle.signal.aborted || !secoes.has(id)) return;
    for (const fonte of pendentes) delete erros[fonte];
    Object.assign(dados, resultado.dados);
    Object.assign(erros, resultado.erros);
    for (const fonte of Object.keys(resultado.dados)) carregadas.add(fonte);
    preencher(id);
    if (pendentes.length) anunciar(pendentes.some((f) => erros[f]) ? `${CARTOES[id].titulo}: ainda não foi possível carregar.` : `${CARTOES[id].titulo} carregado.`);
  }

  function criarCartao(id) {
    const conteudo = el("div", { class: "cartao-conteudo" }, esqueleto());
    conteudo.dataset.id = id;
    const secao = el("section", { class: "cartao", "aria-busy": "true", "aria-label": CARTOES[id].titulo }, edicao.barra(id), conteudo);
    secao.dataset.cartao = id;
    secoes.set(id, secao);
    conteudos.set(id, conteudo);
    limpezas.set(id, []);
    observador.observe(secao);
    return secao;
  }

  function aplicarLayout(cartoes) {
    const ids = new Set(cartoes.map((c) => c.id));
    for (const [id, secao] of secoes) {
      if (ids.has(id)) continue;
      desmontarCartao(id);
      observador.unobserve(secao);
      secao.remove();
      secoes.delete(id);
      conteudos.delete(id);
    }
    for (const { id, largura } of cartoes) {
      const nova = !secoes.has(id);
      const secao = nova ? criarCartao(id) : secoes.get(id);
      secao.classList.remove("t-estreito", "t-largo", "t-inteiro");
      secao.classList.add(`t-${largura}`);
      grade.append(secao);
      if (nova && carregouInicio) {
        if (DEPENDENCIAS[id].every((fonte) => carregadas.has(fonte))) preencher(id);
        else recarregar(id);
      }
    }
    secoes.forEach(ajustarAltura);
  }

  const edicao = criarEdicao({
    grade,
    adicionar,
    titulos: TITULOS,
    aplicarLayout,
    alturaEmLinhas,
    anunciar,
    preferencias: () => preferencias,
    salvar: async (rascunho) => {
      preferencias = await salvarPreferencias(rascunho);
    },
  });

  function cartoesQueUsam(chave) {
    return { lista_transacoes: ["transacoes"], periodo_meses: ["meses"], numeros: ["numeros"] }[chave] ?? [];
  }

  function aplicarPreferencias(parcial) {
    preferencias = { ...preferencias, ...parcial };
    edicao.acompanhar(parcial);
    for (const chave of Object.keys(parcial)) for (const id of cartoesQueUsam(chave)) if (secoes.has(id)) preencher(id);
  }

  function alterarPreferencias(parcial) {
    aplicarPreferencias(parcial);
    salvarDepois(preferencias, () => anunciar("Não foi possível salvar sua preferência. Ela vale só até você sair desta tela."));
  }

  async function salvarAgora(parcial) {
    const salvas = await salvarPreferencias({ ...preferencias, ...parcial });
    aplicarPreferencias({ numeros: salvas.numeros, periodo_meses: salvas.periodo_meses, lista_transacoes: salvas.lista_transacoes });
    anunciar("Preferências salvas.");
  }

  function desenharBotoes() {
    botoes.replaceChildren();
    cabecalhoTela.classList.toggle("editando-cab", edicao.editando());
    if (!edicao.editando()) {
      const personalizar = el("button", { type: "button", class: "btn btn-secundario" }, icone("ajustes"), el("span", { class: "rotulo-curto", texto: "Personalizar" }));
      personalizar.setAttribute("aria-label", "Personalizar o painel");
      personalizar.addEventListener("click", () => {
        mensagem(status, "erro", "");
        edicao.entrar();
        desenharBotoes();
        botoes.querySelector(".btn-primario")?.scrollIntoView({ block: "nearest" });
      });
      botoes.append(personalizar);
      return;
    }
    const cancelar = el("button", { type: "button", class: "btn btn-secundario", texto: "Cancelar" });
    const concluir = el("button", { type: "button", class: "btn btn-primario" }, icone("salvar"), "Concluir");
    cancelar.addEventListener("click", () => {
      mensagem(status, "erro", "");
      edicao.cancelar();
      desenharBotoes();
      botoes.querySelector("button")?.focus();
    });
    concluir.addEventListener("click", async () => {
      mensagem(status, "erro", "");
      ocupado(concluir, true, "Salvando…");
      try {
        await edicao.concluir();
        desenharBotoes();
        botoes.querySelector("button")?.focus();
      } catch (erro) {
        ocupado(concluir, false);
        mensagem(status, "erro", `${erro.message} Suas mudanças continuam aqui; tente concluir de novo.`);
      }
    });
    botoes.append(cancelar, concluir);
  }

  function desenharAviso() {
    avisoSlot.replaceChildren();
    if (!dados.contas) return;
    const aviso = avisoDeContas(dados.contas, contexto);
    if (!aviso) return;
    const [texto, atraso] = textoDoAviso(aviso);
    avisoSlot.append(el("a", { class: `aviso-contas${atraso ? " atraso" : ""}`, href: "#/contas" }, icone("alerta", "ic-sm"), texto));
  }

  function aoSairDaPagina(evento) {
    if (edicao.alterou()) evento.preventDefault();
  }
  addEventListener("beforeunload", aoSairDaPagina);
  definirGuardaDeSaida(
    () =>
      !edicao.alterou() ||
      confirmar({ titulo: "Sair sem salvar o painel?", texto: "As mudanças que você fez na organização do painel vão se perder.", confirmar: "Sair sem salvar", cancelar: "Continuar editando", perigo: true }),
  );

  let carregouInicio = false;
  aplicarLayout(preferencias.cartoes);
  desenharBotoes();

  const necessarias = [...fontesDosCartoes(preferencias.cartoes.map((c) => c.id)), "contas", "categorias"];
  carregarFontes(necessarias, fontes, controle.signal).then((resultado) => {
    if (controle.signal.aborted) return;
    Object.assign(dados, resultado.dados);
    Object.assign(erros, resultado.erros);
    for (const fonte of Object.keys(resultado.dados)) carregadas.add(fonte);
    carregouInicio = true;
    desenharAviso();
    for (const id of secoes.keys()) preencher(id);
  });

  return () => {
    controle.abort();
    observador.disconnect();
    desktop.removeEventListener("change", aoMudarTela);
    removeEventListener("beforeunload", aoSairDaPagina);
    for (const id of limpezas.keys()) desmontarCartao(id);
  };
}
