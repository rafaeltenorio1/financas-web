import { el, icone } from "../dom.js";
import { usuarioAtual } from "../sessao.js";
import { chaveDoMes, compararMeses, hoje, lerChaveDoMes, somarMeses } from "../datas.js";
import { mesAno } from "../formatos.js";
import { avisoDeContas, contextoDoMes } from "../painel/calculos.js";
import { DEPENDENCIAS, carregarFontes, fontesDosCartoes, periodoDoMes } from "../painel/dados.js";
import { lerPreferencias, salvarDepois, salvarPreferencias } from "../painel/preferencias.js";
import { erroDoCartao, esqueleto } from "../painel/componentes.js";
import saldo from "../painel/cartoes/saldo.js";
import transacoes from "../painel/cartoes/transacoes.js";
import { gastosPorCategoria, ganhosPorCategoria } from "../painel/cartoes/categorias.js";
import meses from "../painel/cartoes/meses.js";
import numeros from "../painel/cartoes/numeros.js";
import contas from "../painel/cartoes/contas.js";

const CARTOES = Object.fromEntries([saldo, transacoes, gastosPorCategoria, ganhosPorCategoria, meses, numeros, contas].map((c) => [c.id, c]));
const listaPt = new Intl.ListFormat("pt-BR", { style: "long", type: "conjunction" });

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
  const limpezas = new Map();
  const elementos = new Map();

  const anuncio = el("p", { class: "sr", "aria-live": "polite" });
  const avisoSlot = el("div");
  const grade = el("div", { class: "painel" });
  raiz.append(
    el("header", { class: "painel-cab" }, navegacaoDoMes(mes, contexto.atual)),
    avisoSlot,
    anuncio,
    grade,
  );

  const observador = new ResizeObserver((entradas) => {
    for (const { target } of entradas) ajustarAltura(target);
  });
  const desktop = matchMedia("(min-width: 900px)");
  function ajustarAltura(cartao) {
    if (!desktop.matches) {
      cartao.style.gridRowEnd = "";
      return;
    }
    cartao.style.gridRowEnd = `span ${Math.ceil((cartao.getBoundingClientRect().height + 18) / 4)}`;
  }
  const aoMudarTela = () => elementos.forEach(ajustarAltura);
  desktop.addEventListener("change", aoMudarTela);

  function desmontarCartao(id) {
    for (const limpar of limpezas.get(id) ?? []) limpar();
    limpezas.set(id, []);
  }

  function preencher(id) {
    const cartao = elementos.get(id);
    const definicao = CARTOES[id];
    desmontarCartao(id);
    cartao.replaceChildren();
    cartao.removeAttribute("aria-busy");
    if (DEPENDENCIAS[id].some((fonte) => erros[fonte])) {
      cartao.setAttribute("aria-label", definicao.titulo);
      cartao.append(erroDoCartao(definicao.titulo, () => recarregar(id)));
      return;
    }
    definicao.montar(cartao, {
      dados,
      mes,
      contexto,
      contextoAtual,
      preferencias,
      alterarPreferencias,
      salvarAgora,
      aoDesmontar: (limpar) => limpezas.get(id).push(limpar),
    });
  }

  async function recarregar(id) {
    const cartao = elementos.get(id);
    cartao.replaceChildren(esqueleto());
    cartao.setAttribute("aria-busy", "true");
    const pendentes = DEPENDENCIAS[id].filter((fonte) => erros[fonte] || !(fonte in dados));
    const resultado = await carregarFontes(pendentes, fontes, controle.signal);
    if (controle.signal.aborted) return;
    for (const fonte of pendentes) delete erros[fonte];
    Object.assign(dados, resultado.dados);
    Object.assign(erros, resultado.erros);
    preencher(id);
    anuncio.textContent = erros[pendentes[0]] ? `${CARTOES[id].titulo}: ainda não foi possível carregar.` : `${CARTOES[id].titulo} carregado.`;
  }

  function cartoesQueUsam(chave) {
    return { lista_transacoes: ["transacoes"], periodo_meses: ["meses"], numeros: ["numeros"] }[chave] ?? [];
  }

  function aplicar(parcial) {
    preferencias = { ...preferencias, ...parcial };
    for (const chave of Object.keys(parcial)) for (const id of cartoesQueUsam(chave)) if (elementos.has(id)) preencher(id);
  }

  function alterarPreferencias(parcial) {
    aplicar(parcial);
    salvarDepois(preferencias, () => {
      anuncio.textContent = "Não foi possível salvar sua preferência. Ela vale só até você sair desta tela.";
    });
  }

  async function salvarAgora(parcial) {
    const salvas = await salvarPreferencias({ ...preferencias, ...parcial });
    aplicar(salvas);
    anuncio.textContent = "Preferências salvas.";
  }

  function desenharAviso() {
    avisoSlot.replaceChildren();
    if (!dados.contas) return;
    const aviso = avisoDeContas(dados.contas, contexto);
    if (!aviso) return;
    const [texto, atraso] = textoDoAviso(aviso);
    avisoSlot.append(el("a", { class: `aviso-contas${atraso ? " atraso" : ""}`, href: "#/contas" }, icone("alerta", "ic-sm"), texto));
  }

  for (const { id, largura } of preferencias.cartoes) {
    const cartao = el("section", { class: `cartao t-${largura}`, "aria-busy": "true", "aria-label": CARTOES[id].titulo }, esqueleto());
    cartao.dataset.id = id;
    elementos.set(id, cartao);
    limpezas.set(id, []);
    grade.append(cartao);
    observador.observe(cartao);
  }

  const necessarias = [...fontesDosCartoes(preferencias.cartoes.map((c) => c.id)), "contas", "categorias"];
  carregarFontes(necessarias, fontes, controle.signal).then((resultado) => {
    if (controle.signal.aborted) return;
    Object.assign(dados, resultado.dados);
    Object.assign(erros, resultado.erros);
    desenharAviso();
    for (const id of elementos.keys()) preencher(id);
  });

  return () => {
    controle.abort();
    observador.disconnect();
    desktop.removeEventListener("change", aoMudarTela);
    for (const id of limpezas.keys()) desmontarCartao(id);
  };
}
