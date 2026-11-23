import { api, ErroApi } from "../api.js";
import { el, mensagem, ocupado } from "../dom.js";
import { campo, cartaoDeResultado, marcarErro, selo, telaAuth, validarEmail } from "./auth-comum.js";

export async function montar(raiz) {
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const email = campo({ id: "email", rotulo: "E-mail da conta", type: "email", autocomplete: "email", inputmode: "email", autocapitalize: "none", spellcheck: "false", required: true, maxlength: 255, placeholder: "voce@exemplo.com" });
  const enviar = el("button", { class: "btn btn-primario btn-bloco", type: "submit", texto: "Enviar link" });
  const form = el("form", { class: "auth-form", novalidate: true }, email.bloco, enviar);
  const cartao = el(
    "section",
    { class: "auth-cartao", "aria-labelledby": "titulo-esqueci" },
    selo("cadeado"),
    el("h1", { class: "auth-titulo", id: "titulo-esqueci", texto: "Esqueci a senha" }),
    el("p", { class: "auth-sub", texto: "Informe o e-mail da sua conta e enviaremos um link para você criar uma senha nova." }),
    aviso,
    form,
    el("p", { class: "auth-rodape" }, "Lembrou? ", el("a", { href: "#/entrar", texto: "Voltar para o login" })),
  );
  raiz.append(telaAuth(cartao));
  email.entrada.setAttribute("data-foco-inicial", "");
  email.entrada.addEventListener("input", () => marcarErro(email, ""));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(aviso, "erro", "");
    if (!validarEmail(email)) {
      email.entrada.focus();
      return;
    }
    ocupado(enviar, true, "Enviando…");
    try {
      const resposta = await api.post("/auth/esqueci-senha", { email: email.entrada.value.trim() });
      const resultado = cartaoDeResultado({
        simbolo: "sucesso",
        titulo: "Confira seu e-mail",
        texto: resposta.mensagem,
        aviso: el("p", { class: "auth-sub", texto: "O link vale por pouco tempo e só pode ser usado uma vez. Se não chegar, olhe a caixa de spam." }),
        acoes: [el("a", { class: "btn btn-secundario btn-bloco", href: "#/entrar", texto: "Voltar para o login" })],
      });
      cartao.replaceWith(resultado);
      resultado.querySelector("h1").focus();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      mensagem(aviso, erro.status === 429 ? "aviso" : "erro", erro.message);
    } finally {
      ocupado(enviar, false);
    }
  });
}
