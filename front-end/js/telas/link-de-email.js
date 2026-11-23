import { api, ErroApi } from "../api.js";
import { el, mensagem, ocupado } from "../dom.js";
import { carregarUsuario } from "../sessao.js";
import { cartaoDeResultado, lerTokenDaUrl, selo, telaAuth } from "./auth-comum.js";

export function telaDeConfirmacao({ caminho, rota, carregando, sucesso, invalido, podeReenviar }) {
  return async function montar(raiz, { parametros }) {
    const token = lerTokenDaUrl(parametros, caminho);
    const usuario = await carregarUsuario().catch(() => null);
    const acaoPrincipal = usuario
      ? el("a", { class: "btn btn-primario btn-bloco", href: "#/", texto: "Ir para o painel" })
      : el("a", { class: "btn btn-primario btn-bloco", href: "#/entrar", texto: "Entrar" });

    const espera = el(
      "section",
      { class: "auth-cartao", "aria-labelledby": "titulo-link", "aria-busy": "true" },
      selo("escudo"),
      el("h1", { class: "auth-titulo", id: "titulo-link", texto: carregando }),
      el("p", { class: "auth-carregando", role: "status" }, el("span", { class: "girando", "aria-hidden": "true" }), "Só um instante…"),
    );
    raiz.append(telaAuth(espera));

    function mostrar(cartao) {
      espera.replaceWith(cartao);
      cartao.querySelector("h1").focus();
    }

    function falha(texto) {
      const acoes = [];
      if (podeReenviar && usuario && !usuario.email_verificado) {
        const reenviar = el("button", { type: "button", class: "btn btn-primario btn-bloco", texto: "Enviar um novo link" });
        const retorno = el("div", { class: "mensagem", role: "alert" });
        reenviar.addEventListener("click", async () => {
          ocupado(reenviar, true, "Enviando…");
          try {
            const resposta = await api.post("/auth/verificar-email/reenviar");
            mensagem(retorno, "sucesso", `${resposta.mensagem} Confira ${usuario.email}.`);
          } catch (erro) {
            if (!(erro instanceof ErroApi)) throw erro;
            mensagem(retorno, erro.status === 429 ? "aviso" : "erro", erro.message);
          } finally {
            ocupado(reenviar, false);
          }
        });
        acoes.push(reenviar, retorno);
      } else if (podeReenviar && !usuario) {
        acoes.push(el("p", { class: "auth-sub", texto: "Entre na sua conta para pedir um novo link." }));
      }
      acoes.push(usuario ? acaoPrincipal : el("a", { class: "btn btn-secundario btn-bloco", href: "#/entrar", texto: "Entrar" }));
      mostrar(cartaoDeResultado({ simbolo: "alerta", titulo: invalido, texto, acoes }));
    }

    if (!token) {
      falha("O link está incompleto. Abra de novo o link do e-mail ou copie o endereço inteiro.");
      return;
    }
    try {
      await api.post(rota, { token });
      if (usuario) await carregarUsuario({ forcar: true }).catch(() => null);
      mostrar(cartaoDeResultado({ simbolo: "sucesso", titulo: sucesso.titulo, texto: sucesso.texto, acoes: [acaoPrincipal] }));
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      falha(erro.status === 400 ? "Links de confirmação expiram e só podem ser usados uma vez." : erro.message);
    }
  };
}
