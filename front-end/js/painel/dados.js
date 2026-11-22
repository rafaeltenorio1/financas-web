import { api } from "../api.js";
import { carregarCategorias } from "../categorias.js";
import { inicioDoMes, somarMeses } from "../datas.js";

function consulta(parametros) {
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros)) if (valor !== undefined && valor !== null) busca.set(chave, String(valor));
  return busca.toString();
}

export function periodoDoMes(mes, fuso) {
  return {
    inicio: inicioDoMes(mes, fuso).toISOString(),
    fim: inicioDoMes(somarMeses(mes, 1), fuso).toISOString(),
    inicioHistorico: inicioDoMes(somarMeses(mes, -11), fuso).toISOString(),
  };
}

export const FONTES = {
  resumo: ({ periodo, fuso }, sinal) =>
    api.get(`/transacoes/resumo?${consulta({ data_inicio: periodo.inicio, data_fim: periodo.fim, fuso })}`, { sinal }),
  historico: ({ periodo, fuso }, sinal) =>
    api.get(`/transacoes/resumo?${consulta({ data_inicio: periodo.inicioHistorico, data_fim: periodo.fim, fuso })}`, { sinal }),
  despesas: ({ periodo }, sinal) =>
    api.get(`/transacoes?${consulta({ data_inicio: periodo.inicio, data_fim: periodo.fim, tipo: "despesa", limit: 12 })}`, { sinal }),
  receitas: ({ periodo }, sinal) =>
    api.get(`/transacoes?${consulta({ data_inicio: periodo.inicio, data_fim: periodo.fim, tipo: "receita", limit: 12 })}`, { sinal }),
  contas: (_contexto, sinal) => api.get(`/contas-recorrentes?${consulta({ ativa: true, tipo: "despesa", limit: 100 })}`, { sinal }),
  categorias: () => carregarCategorias(),
};

export const DEPENDENCIAS = {
  saldo: ["resumo"],
  transacoes: ["despesas", "receitas", "resumo", "categorias"],
  categorias: ["resumo", "categorias"],
  origem: ["resumo", "categorias"],
  meses: ["historico"],
  numeros: ["resumo", "historico", "contas"],
  contas: ["contas", "categorias"],
};

export async function carregarFontes(nomes, contexto, sinal) {
  const lista = [...new Set(nomes)];
  const resultados = await Promise.allSettled(lista.map((nome) => FONTES[nome](contexto, sinal)));
  const dados = {};
  const erros = {};
  resultados.forEach((resultado, i) => {
    if (resultado.status === "fulfilled") dados[lista[i]] = resultado.value;
    else if (resultado.reason?.name !== "AbortError") erros[lista[i]] = resultado.reason;
  });
  return { dados, erros };
}

export function fontesDosCartoes(ids) {
  return ids.flatMap((id) => DEPENDENCIAS[id] || []);
}
