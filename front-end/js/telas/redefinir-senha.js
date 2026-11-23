import { api, ErroApi } from "../api.js";
import { el, mensagem, ocupado } from "../dom.js";
import { encerrarLocalmente } from "../sessao.js";
import { campoSenha, cartaoDeResultado, lerTokenDaUrl, marcarErro, medidorDeForca, selo, telaAuth, validarSenhaNova } from "./auth-comum.js";

function linkInvalido() {
  return cartaoDeResultado({
    simbolo: "alerta",
    titulo: "Este link não vale mais",
    texto: "Links de redefinição expiram em pouco tempo e só podem ser usados uma vez. Peça um novo.",
    acoes: [
      el("a", { class: "btn btn-primario btn-bloco", href: "#/esqueci-senha", texto: "Pedir um novo link" }),
      el("a", { class: "btn btn-secundario btn-bloco", href: "#/entrar", texto: "Voltar para o login" }),
    ],
  });
}

export async function montar(raiz, { parametros }) {
  const token = lerTokenDaUrl(parametros, "/redefinir-senha");
  if (!token) {
    raiz.append(telaAuth(linkInvalido()));
    return;
  }
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const nova = campoSenha({ id: "senha-nova", rotulo: "Senha nova", autocomplete: "new-password", required: true, maxlength: 128 });
  nova.bloco.insertBefore(medidorDeForca(nova.entrada), nova.erro);
  const repetir = campoSenha({ id: "senha-repetida", rotulo: "Repita a senha nova", autocomplete: "new-password", required: true, maxlength: 128 });
  const salvar = el("button", { class: "btn btn-primario btn-bloco", type: "submit", texto: "Salvar senha nova" });
  const form = el("form", { class: "auth-form", novalidate: true }, nova.bloco, repetir.bloco, salvar);
  const cartao = el(
    "section",
    { class: "auth-cartao", "aria-labelledby": "titulo-redefinir" },
    selo("cadeado"),
    el("h1", { class: "auth-titulo", id: "titulo-redefinir", texto: "Criar senha nova" }),
    el("p", { class: "auth-sub", texto: "Ao salvar, todas as sessões abertas da sua conta serão encerradas." }),
    aviso,
    form,
  );
  raiz.append(telaAuth(cartao));
  nova.entrada.setAttribute("data-foco-inicial", "");
  for (const c of [nova, repetir]) c.entrada.addEventListener("input", () => marcarErro(c, ""));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(aviso, "erro", "");
    const ok = validarSenhaNova(nova);
    marcarErro(repetir, repetir.entrada.value === nova.entrada.value ? "" : "As duas senhas não são iguais.");
    if (!ok || repetir.entrada.hasAttribute("aria-invalid")) {
      (ok ? repetir : nova).entrada.focus();
      return;
    }
    ocupado(salvar, true, "Salvando…");
    try {
      await api.post("/auth/redefinir-senha", { token, senha_nova: nova.entrada.value });
      encerrarLocalmente();
      const resultado = cartaoDeResultado({
        simbolo: "sucesso",
        titulo: "Senha nova salva",
        texto: "Seu e-mail também ficou confirmado. Entre com a senha nova.",
        acoes: [el("a", { class: "btn btn-primario btn-bloco", href: "#/entrar", texto: "Entrar" })],
      });
      cartao.replaceWith(resultado);
      resultado.querySelector("h1").focus();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.status === 400) {
        const invalido = linkInvalido();
        cartao.replaceWith(invalido);
        invalido.querySelector("h1").focus();
      } else if (erro.status === 422) {
        marcarErro(nova, "Confira a senha: ela precisa ter de 8 a 128 caracteres.");
        nova.entrada.focus();
      } else {
        mensagem(aviso, "erro", erro.message);
      }
    } finally {
      ocupado(salvar, false);
    }
  });
}
