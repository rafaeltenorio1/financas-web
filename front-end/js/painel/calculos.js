import { chaveDoDia, chaveDoMes, compararMeses, diasEntre, diasNoMes, somarMeses } from "../datas.js";

export const CATEGORIAS_ASSINATURA = ["Streaming de Música", "Streaming de Vídeo", "Nuvem e Softwares"];
const FORMA_CREDITO = "cartao de credito";

const n = (valor) => Number(valor ?? 0);

export function contextoDoMes(mes, hojeLocal) {
  const comparacao = compararMeses(mes, hojeLocal);
  const dias = diasNoMes(mes);
  return {
    mes,
    atual: comparacao === 0,
    passado: comparacao < 0,
    dias,
    diasDecorridos: comparacao === 0 ? hojeLocal.dia : comparacao < 0 ? dias : 0,
    hoje: chaveDoDia(hojeLocal),
    fimDoMes: chaveDoDia({ ...mes, dia: dias }),
  };
}

export function saldo(resumo) {
  const receitas = n(resumo.receitas);
  const despesas = n(resumo.despesas);
  return {
    receitas,
    despesas,
    saldo: n(resumo.saldo),
    guardadoPct: receitas > 0 ? Math.round(((receitas - despesas) / receitas) * 100) : null,
    gastoPct: receitas > 0 ? Math.round((despesas / receitas) * 100) : null,
  };
}

export function mesesDoHistorico(historico, mes, quantidade) {
  const porChave = new Map((historico?.por_mes ?? []).map((m) => [m.mes, m]));
  return Array.from({ length: quantidade }, (_, i) => {
    const alvo = somarMeses(mes, i - quantidade + 1);
    const achado = porChave.get(chaveDoMes(alvo));
    return {
      ...alvo,
      chave: chaveDoMes(alvo),
      receitas: n(achado?.receitas),
      despesas: n(achado?.despesas),
      categorias: achado?.categorias ?? [],
      atual: i === quantidade - 1,
    };
  });
}

export function mediaDeGastos(historico, mes) {
  const anteriores = mesesDoHistorico(historico, mes, 12).slice(0, -1).filter((m) => m.receitas > 0 || m.despesas > 0);
  if (!anteriores.length) return null;
  return { media: anteriores.reduce((s, m) => s + m.despesas, 0) / anteriores.length, meses: anteriores.length };
}

export function categoriasDoTipo(lista, tipo, limite = 5) {
  const doTipo = (lista ?? []).filter((c) => c.tipo === tipo).map((c) => ({ ...c, total: n(c.total) }));
  doTipo.sort((a, b) => b.total - a.total);
  const topo = doTipo.slice(0, limite);
  const resto = doTipo.slice(limite);
  if (resto.length) {
    topo.push({
      id_categoria: null,
      nome: "Outras",
      cor: null,
      tipo,
      outras: true,
      total: resto.reduce((s, c) => s + c.total, 0),
      quantidade: resto.reduce((s, c) => s + c.quantidade, 0),
    });
  }
  return topo;
}

export function contasDoMes(contas, contexto) {
  return (contas ?? [])
    .filter((c) => c.ativa && c.tipo === "despesa")
    .map((c) => ({ ...c, valor: n(c.valor), dias: diasEntre(contexto.hoje, c.proximo_vencimento) }))
    .sort((a, b) => a.proximo_vencimento.localeCompare(b.proximo_vencimento));
}

export function contasAVencer(contas, contexto) {
  return contasDoMes(contas, contexto).filter((c) => c.proximo_vencimento <= contexto.fimDoMes);
}

export function avisoDeContas(contas, contexto, janelaDias = 7) {
  if (!contexto.atual) return null;
  const proximas = contasDoMes(contas, contexto).filter((c) => c.dias <= janelaDias);
  if (!proximas.length) return null;
  const atrasadas = proximas.filter((c) => c.dias < 0);
  return { contas: proximas, atrasadas: atrasadas.length };
}

const SO_MES_ATUAL = { indisponivel: "Só no mês atual" };

export const NUMEROS = {
  previsao: {
    rotulo: "Previsão de gastos no mês",
    calcular({ resumo, contas, contexto }) {
      if (!contexto.atual) return SO_MES_ATUAL;
      const despesas = n(resumo.despesas);
      const variaveis = despesas - n(resumo.despesas_fixas);
      const pendentes = contasAVencer(contas, contexto).reduce((s, c) => s + c.valor, 0);
      const ritmo = contexto.diasDecorridos ? variaveis / contexto.diasDecorridos : 0;
      return { valor: despesas + pendentes + ritmo * (contexto.dias - contexto.diasDecorridos), detalhe: "no ritmo atual, com as contas que faltam" };
    },
  },
  pagar: {
    rotulo: "Contas a pagar",
    calcular({ contas, contexto }) {
      if (!contexto.atual) return SO_MES_ATUAL;
      const lista = contasAVencer(contas, contexto);
      if (!lista.length) return { valor: 0, detalhe: "nenhuma conta até o fim do mês" };
      const atrasadas = lista.filter((c) => c.dias < 0).length;
      return {
        valor: lista.reduce((s, c) => s + c.valor, 0),
        detalhe: atrasadas ? `${lista.length} contas, ${atrasadas} em atraso` : `${lista.length} ${lista.length === 1 ? "conta" : "contas"} até o fim do mês`,
      };
    },
  },
  media: {
    rotulo: "Média de gasto por dia",
    calcular({ resumo, contexto }) {
      if (!contexto.diasDecorridos) return SO_MES_ATUAL;
      return { valor: (n(resumo.despesas) - n(resumo.despesas_fixas)) / contexto.diasDecorridos, detalhe: "sem contar as contas fixas" };
    },
  },
  credito: {
    rotulo: "No cartão de crédito",
    calcular({ resumo }) {
      const linha = (resumo.por_forma_pagamento ?? []).find((f) => f.forma_pagamento === FORMA_CREDITO && f.tipo === "despesa");
      const quantidade = linha?.quantidade ?? 0;
      return { valor: n(linha?.total), detalhe: `${quantidade} ${quantidade === 1 ? "compra" : "compras"} neste mês` };
    },
  },
  fixos: {
    rotulo: "Gastos fixos",
    calcular({ resumo }) {
      const fixas = n(resumo.despesas_fixas);
      const despesas = n(resumo.despesas);
      return { valor: fixas, detalhe: despesas ? `${Math.round((fixas / despesas) * 100)}% de tudo que saiu` : "nenhum gasto no mês" };
    },
  },
  maior: {
    rotulo: "Maior gasto",
    calcular({ resumo }) {
      const maior = resumo.maior_despesa;
      if (!maior) return { valor: 0, detalhe: "nenhum gasto no mês" };
      return { valor: n(maior.valor), detalhe: maior.nome || "Sem nome", data: maior.data_hora };
    },
  },
  guardado: {
    rotulo: "Quanto guardou",
    calcular({ resumo }) {
      const { guardadoPct } = saldo(resumo);
      if (guardadoPct === null) return { texto: "—", detalhe: "nenhum ganho no mês" };
      if (guardadoPct < 0) return { texto: "0%", detalhe: "gastou mais do que ganhou" };
      return { texto: `${guardadoPct}%`, detalhe: "do que entrou no mês" };
    },
  },
  quantidade: {
    rotulo: "Transações no mês",
    calcular({ resumo }) {
      const contar = (tipo) => (resumo.por_categoria ?? []).filter((c) => c.tipo === tipo).reduce((s, c) => s + c.quantidade, 0);
      const despesas = contar("despesa");
      const receitas = contar("receita");
      return { texto: String(despesas + receitas), detalhe: `${despesas} despesas e ${receitas} receitas` };
    },
  },
  assinaturas: {
    rotulo: "Assinaturas",
    calcular({ resumo }) {
      const linhas = (resumo.por_categoria ?? []).filter((c) => c.tipo === "despesa" && CATEGORIAS_ASSINATURA.includes(c.nome));
      return { valor: linhas.reduce((s, c) => s + n(c.total), 0), detalhe: "streaming, nuvem e programas" };
    },
  },
  media12: {
    rotulo: "Gasto médio por mês",
    calcular({ historico, contexto }) {
      const media = mediaDeGastos(historico, contexto.mes);
      if (!media) return { texto: "—", detalhe: "ainda sem meses anteriores" };
      return { valor: media.media, detalhe: `nos ${media.meses} ${media.meses === 1 ? "mês anterior" : "meses anteriores"}` };
    },
  },
};

export function calcularNumero(id, dados) {
  try {
    return NUMEROS[id].calcular(dados);
  } catch {
    return { indisponivel: "Não foi possível calcular" };
  }
}
