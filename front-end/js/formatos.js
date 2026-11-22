import { FUSO_PADRAO } from "./config.js";

let fuso = FUSO_PADRAO;
const cache = new Map();

export function definirFuso(novo) {
  if (novo && novo !== fuso) {
    fuso = novo;
    cache.clear();
  }
}

function formatador(chave, opcoes) {
  if (!cache.has(chave)) cache.set(chave, new Intl.DateTimeFormat("pt-BR", { timeZone: fuso, ...opcoes }));
  return cache.get(chave);
}

const moedaFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function moeda(valor) {
  return moedaFmt.format(Number(valor));
}

export function moedaComSinal(valor, tipo) {
  return `${tipo === "receita" ? "+" : "−"} ${moeda(valor)}`;
}

export function moedaCurta(valor) {
  const n = Number(valor);
  if (Math.abs(n) < 1000) return moeda(n);
  return `R$ ${(n / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`;
}

export function dataCurta(iso) {
  return formatador("curta", { day: "2-digit", month: "short" }).format(new Date(iso));
}

export function dataLonga(iso) {
  return formatador("longa", { weekday: "long", day: "numeric", month: "long" }).format(new Date(iso));
}

export function mesAno(iso) {
  return formatador("mes-ano", { month: "long", year: "numeric" }).format(new Date(iso));
}

export function hora(iso) {
  return formatador("hora", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}
