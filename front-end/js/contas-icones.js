import { api } from "./api.js";

let cache = null;
let pedido = null;

export async function carregarIconesDasContas({ forcar = false } = {}) {
  if (cache && !forcar) return cache;
  pedido ??= api
    .get("/contas-recorrentes?limit=100")
    .then((lista) => {
      cache = new Map(lista.map((c) => [c.id_conta_recorrente, c.icone]));
      return cache;
    })
    .finally(() => (pedido = null));
  return pedido;
}

export function esquecerIconesDasContas() {
  cache = null;
}

export function iconeDaContaRecorrente(id) {
  return id ? cache?.get(id) ?? null : null;
}
