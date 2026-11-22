import { api } from "../api.js";
import { definirUsuario } from "../sessao.js";

export const CARTOES = ["saldo", "transacoes", "categorias", "origem", "meses", "numeros", "contas"];
export const LARGURAS = ["estreito", "largo", "inteiro"];
export const NUMEROS = ["previsao", "pagar", "media", "credito", "fixos", "maior", "guardado", "quantidade", "assinaturas", "media12"];
export const PERIODOS = [2, 3, 12];
export const LISTAS = ["lista", "colunas"];

export const PADRAO = Object.freeze({
  cartoes: [
    { id: "saldo", largura: "estreito" },
    { id: "transacoes", largura: "largo" },
    { id: "categorias", largura: "estreito" },
    { id: "meses", largura: "largo" },
    { id: "numeros", largura: "estreito" },
  ],
  numeros: ["previsao", "pagar", "media", "credito", "fixos", "maior"],
  periodo_meses: 3,
  lista_transacoes: "colunas",
});

export function copiaDoPadrao() {
  return structuredClone(PADRAO);
}

export function lerPreferencias(usuario) {
  const salvas = usuario?.preferencias_painel;
  if (!salvas || typeof salvas !== "object") return copiaDoPadrao();
  const vistos = new Set();
  const cartoes = (Array.isArray(salvas.cartoes) ? salvas.cartoes : [])
    .filter((c) => CARTOES.includes(c?.id) && LARGURAS.includes(c?.largura) && !vistos.has(c.id) && vistos.add(c.id))
    .map((c) => ({ id: c.id, largura: c.largura }));
  const numeros = [...new Set((Array.isArray(salvas.numeros) ? salvas.numeros : []).filter((n) => NUMEROS.includes(n)))];
  return {
    cartoes,
    numeros,
    periodo_meses: PERIODOS.includes(salvas.periodo_meses) ? salvas.periodo_meses : PADRAO.periodo_meses,
    lista_transacoes: LISTAS.includes(salvas.lista_transacoes) ? salvas.lista_transacoes : PADRAO.lista_transacoes,
  };
}

export async function salvarPreferencias(preferencias) {
  const usuario = await api.patch("/auth/me", { preferencias_painel: preferencias });
  definirUsuario(usuario);
  return lerPreferencias(usuario);
}

export async function voltarAoPadrao() {
  const usuario = await api.patch("/auth/me", { preferencias_painel: null });
  definirUsuario(usuario);
  return lerPreferencias(usuario);
}

let temporizador = null;
let pendente = null;

export function salvarDepois(preferencias, aoFalhar, atraso = 700) {
  pendente = structuredClone(preferencias);
  clearTimeout(temporizador);
  temporizador = setTimeout(async () => {
    const enviar = pendente;
    pendente = null;
    try {
      await salvarPreferencias(enviar);
    } catch (erro) {
      aoFalhar?.(erro);
    }
  }, atraso);
}

export function cancelarSalvamentoPendente() {
  clearTimeout(temporizador);
  pendente = null;
}
