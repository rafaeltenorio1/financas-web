import { api, esquecerCsrf, ErroApi } from "./api.js";
import { definirFuso } from "./formatos.js";

let usuario = null;
let verificado = false;

export function usuarioAtual() {
  return usuario;
}

export function definirUsuario(dados) {
  usuario = dados;
  verificado = true;
  if (dados?.fuso) definirFuso(dados.fuso);
}

export async function carregarUsuario({ forcar = false } = {}) {
  if (verificado && !forcar) return usuario;
  try {
    definirUsuario(await api.get("/auth/me"));
  } catch (erro) {
    if (!(erro instanceof ErroApi) || erro.status !== 401) throw erro;
    definirUsuario(null);
  }
  return usuario;
}

export function encerrarLocalmente() {
  usuario = null;
  verificado = true;
  esquecerCsrf();
}

export async function sair() {
  try {
    await api.post("/auth/logout");
  } finally {
    encerrarLocalmente();
  }
}
