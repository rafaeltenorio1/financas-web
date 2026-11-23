import { api, ErroApi } from "../api.js";
import { el, mensagem, ocupado } from "../dom.js";
import { campo, campoSenha, cartaoDeResultado, marcarErro, medidorDeForca, selo, telaAuth, validarEmail, validarSenhaNova } from "./auth-comum.js";

const CAMPOS_DA_API = { nome: "Confira o nome.", email: "Confira o e-mail.", senha: "Confira a senha." };

export async function montar(raiz) {
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const nome = campo({ id: "nome", rotulo: "Como podemos te chamar?", autocomplete: "name", required: true, maxlength: 255, placeholder: "Seu nome" });
  const email = campo({ id: "email", rotulo: "E-mail", type: "email", autocomplete: "email", inputmode: "email", autocapitalize: "none", spellcheck: "false", required: true, maxlength: 255, placeholder: "voce@exemplo.com" });
  const senha = campoSenha({ id: "senha", rotulo: "Senha", autocomplete: "new-password", required: true, maxlength: 128 });
  senha.bloco.insertBefore(medidorDeForca(senha.entrada), senha.erro);
  const criar = el("button", { class: "btn btn-primario btn-bloco", type: "submit", texto: "Criar conta" });
  const form = el("form", { class: "auth-form", novalidate: true }, nome.bloco, email.bloco, senha.bloco, criar);
  const cartao = el(
    "section",
    { class: "auth-cartao", "aria-labelledby": "titulo-cadastro" },
    selo("conta"),
    el("h1", { class: "auth-titulo", id: "titulo-cadastro", texto: "Criar conta" }),
    el("p", { class: "auth-sub", texto: "Leva menos de um minuto. Depois é só confirmar o e-mail." }),
    aviso,
    form,
    el("p", { class: "auth-rodape" }, "Já tem conta? ", el("a", { href: "#/entrar", texto: "Entrar" })),
  );
  raiz.append(telaAuth(cartao));
  nome.entrada.setAttribute("data-foco-inicial", "");

  for (const c of [nome, email, senha]) c.entrada.addEventListener("input", () => marcarErro(c, ""));

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(aviso, "erro", "");
    marcarErro(nome, nome.entrada.value.trim() ? "" : "Informe seu nome.");
    const validos = [!nome.entrada.hasAttribute("aria-invalid"), validarEmail(email), validarSenhaNova(senha)];
    if (validos.includes(false)) {
      [nome, email, senha].find((c) => c.entrada.hasAttribute("aria-invalid"))?.entrada.focus();
      return;
    }
    ocupado(criar, true, "Criando conta…");
    try {
      const endereco = email.entrada.value.trim();
      const resposta = await api.post("/auth/register", { nome: nome.entrada.value.trim(), email: endereco, senha: senha.entrada.value });
      const resultado = cartaoDeResultado({
        simbolo: "sucesso",
        titulo: "Confira seu e-mail",
        texto: resposta.mensagem,
        destaque: endereco,
        aviso: el("p", { class: "auth-sub", texto: "Não chegou em alguns minutos? Olhe a caixa de spam. Você já pode entrar enquanto isso." }),
        acoes: [el("a", { class: "btn btn-primario btn-bloco", href: "#/entrar", texto: "Ir para o login" })],
      });
      cartao.replaceWith(resultado);
      resultado.querySelector("h1").focus();
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      const campos = Object.keys(erro.campos).filter((c) => c in CAMPOS_DA_API);
      if (erro.status === 422 && campos.length) {
        for (const c of campos) marcarErro({ nome, email, senha }[c], CAMPOS_DA_API[c]);
        ({ nome, email, senha })[campos[0]].entrada.focus();
      } else {
        mensagem(aviso, "erro", erro.message);
      }
    } finally {
      ocupado(criar, false);
    }
  });
}
