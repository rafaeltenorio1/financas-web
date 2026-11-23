import { API_URL } from "./config.js";

const ALTERAM = new Set(["POST", "PUT", "PATCH", "DELETE"]);

const PUBLICAS = new Set([
  "/auth/login",
  "/auth/login/2fa",
  "/auth/register",
  "/auth/esqueci-senha",
  "/auth/redefinir-senha",
  "/auth/verificar-email",
  "/auth/trocar-email/confirmar",
]);

const CREDENCIAL_ERRADA = new Set([
  "/auth/trocar-senha",
  "/auth/excluir-conta",
  "/auth/trocar-email",
  "/auth/2fa/ativar",
  "/auth/2fa/desativar",
  "/auth/2fa/codigos-recuperacao",
]);

const SEM_CONEXAO = "Não foi possível falar com o servidor. Confira sua conexão e tente de novo.";
const ERRO_GENERICO = "Algo deu errado do nosso lado. Tente de novo em instantes.";

export class ErroApi extends Error {
  constructor(status, mensagem, { campos = {}, esperarSegundos = null, detalhe = null } = {}) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
    this.campos = campos;
    this.detalhe = detalhe;
    this.esperarSegundos = esperarSegundos;
  }
}

let csrf = null;
let pedidoCsrf = null;

export function esquecerCsrf() {
  csrf = null;
  pedidoCsrf = null;
}

async function obterCsrf() {
  if (csrf) return csrf;
  pedidoCsrf ??= requisitar("/auth/csrf").then((r) => (csrf = r.csrf_token)).finally(() => (pedidoCsrf = null));
  return pedidoCsrf;
}

function caminhoSemConsulta(caminho) {
  return caminho.split("?")[0];
}

function camposInvalidos(detalhe) {
  const campos = {};
  if (!Array.isArray(detalhe)) return campos;
  for (const erro of detalhe) {
    const campo = Array.isArray(erro.loc) ? erro.loc.at(-1) : null;
    if (typeof campo === "string" && !(campo in campos)) campos[campo] = erro.type || "invalido";
  }
  return campos;
}

function mensagemDoErro(status, dados) {
  if (typeof dados?.detail === "string") return dados.detail;
  if (typeof dados?.detail?.mensagem === "string") return dados.detail.mensagem;
  if (status === 422) return "Confira os campos destacados.";
  if (status === 401) return "Sua sessão expirou. Entre novamente.";
  if (status === 403) return "Requisição não permitida.";
  if (status === 404) return "Não encontramos o que você procurou.";
  if (status === 429) return "Muitas tentativas. Aguarde um pouco e tente de novo.";
  return ERRO_GENERICO;
}

async function lerCorpo(resposta, formato) {
  if (resposta.status === 204) return null;
  if (formato === "blob") return resposta.blob();
  const tipo = resposta.headers.get("content-type") || "";
  if (tipo.includes("application/json")) return resposta.json();
  return resposta.text();
}

async function requisitar(caminho, { metodo = "GET", corpo, sinal, formato = "json", repetida = false } = {}) {
  const rota = caminhoSemConsulta(caminho);
  const cabecalhos = { Accept: "application/json" };
  if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
  const precisaCsrf = ALTERAM.has(metodo) && !PUBLICAS.has(rota);
  if (precisaCsrf) cabecalhos["X-CSRF-Token"] = await obterCsrf();

  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      credentials: "include",
      signal: sinal,
    });
  } catch (erro) {
    if (erro.name === "AbortError") throw erro;
    throw new ErroApi(0, SEM_CONEXAO);
  }

  if (resposta.status === 403 && precisaCsrf && !repetida) {
    esquecerCsrf();
    return requisitar(caminho, { metodo, corpo, sinal, formato, repetida: true });
  }

  let dados = null;
  try {
    dados = await lerCorpo(resposta, resposta.ok ? formato : "json");
  } catch {
    dados = null;
  }

  if (resposta.ok) return dados;

  if (resposta.status === 401 && !PUBLICAS.has(rota) && !CREDENCIAL_ERRADA.has(rota)) {
    esquecerCsrf();
    window.dispatchEvent(new CustomEvent("sessao-expirada"));
  }

  const espera = Number(resposta.headers.get("Retry-After"));
  throw new ErroApi(resposta.status, mensagemDoErro(resposta.status, dados), {
    campos: resposta.status === 422 ? camposInvalidos(dados?.detail) : {},
    esperarSegundos: Number.isFinite(espera) && espera > 0 ? espera : null,
    detalhe: dados?.detail ?? null,
  });
}

export async function baixarArquivo(caminho, nomePadrao) {
  let resposta;
  try {
    resposta = await fetch(API_URL + caminho, { credentials: "include", headers: { Accept: "text/csv" } });
  } catch {
    throw new ErroApi(0, SEM_CONEXAO);
  }
  if (!resposta.ok) {
    let dados = null;
    try {
      dados = await resposta.json();
    } catch {
      dados = null;
    }
    if (resposta.status === 401) window.dispatchEvent(new CustomEvent("sessao-expirada"));
    throw new ErroApi(resposta.status, mensagemDoErro(resposta.status, dados));
  }
  const cabecalho = resposta.headers.get("Content-Disposition") || "";
  const nome = /filename="([^"]+)"/.exec(cabecalho)?.[1] ?? nomePadrao;
  const url = URL.createObjectURL(await resposta.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return nome;
}

export const api = {
  get: (caminho, opcoes) => requisitar(caminho, { ...opcoes, metodo: "GET" }),
  post: (caminho, corpo, opcoes) => requisitar(caminho, { ...opcoes, metodo: "POST", corpo }),
  patch: (caminho, corpo, opcoes) => requisitar(caminho, { ...opcoes, metodo: "PATCH", corpo }),
  put: (caminho, corpo, opcoes) => requisitar(caminho, { ...opcoes, metodo: "PUT", corpo }),
  delete: (caminho, opcoes) => requisitar(caminho, { ...opcoes, metodo: "DELETE" }),
};
