import { api, ErroApi } from "../api.js";
import { DESAFIO_2FA_MIN } from "../config.js";
import { el, icone, mensagem, ocupado } from "../dom.js";
import { definirUsuario } from "../sessao.js";
import { mensagemParaProximaTela } from "../app.js";
import { telaAuth, selo, campo, campoSenha, marcarErro, destinoSeguro } from "./auth-comum.js";

const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MODOS = {
  app: {
    rotulo: "Código do aplicativo",
    ajuda: "Os 6 números que aparecem no seu aplicativo autenticador.",
    placeholder: "000000",
    inputmode: "numeric",
    autocomplete: "one-time-code",
    troca: "Usar um código de recuperação",
    instrucao: `Abra seu aplicativo autenticador e digite o código. Você tem ${DESAFIO_2FA_MIN} minutos.`,
  },
  recuperacao: {
    rotulo: "Código de recuperação",
    ajuda: "Um dos 10 códigos que você guardou ao ativar a verificação em duas etapas.",
    placeholder: "XXXX-XXXX-XXXX-XXXX",
    inputmode: "text",
    autocomplete: "off",
    troca: "Usar o código do aplicativo",
    instrucao: `Sem acesso ao aplicativo? Use um dos seus códigos de recuperação. Cada um funciona uma única vez.`,
  },
};

function textoDeEspera(erro) {
  if (!erro.esperarSegundos) return erro.message;
  const minutos = Math.ceil(erro.esperarSegundos / 60);
  return `Muitas tentativas de login. Tente de novo em ${minutos} ${minutos === 1 ? "minuto" : "minutos"}.`;
}

export async function montar(raiz, { parametros, navegar }) {
  const destino = destinoSeguro(parametros.get("volta"));
  let inicioDesafio = 0;
  let modo = "app";

  const avisoSenha = el("div", { class: "mensagem", role: "alert" });
  const email = campo({ id: "email", rotulo: "E-mail", type: "email", autocomplete: "username", inputmode: "email", autocapitalize: "none", spellcheck: "false", placeholder: "voce@exemplo.com", required: true, maxlength: 255 });
  const senha = campoSenha({
    id: "senha",
    rotulo: "Senha",
    autocomplete: "current-password",
    required: true,
    maxlength: 128,
    acessorio: el("a", { class: "link-pequeno", href: "#/esqueci-senha", texto: "Esqueci a senha" }),
  });
  const lembrar = el("input", { type: "checkbox", id: "lembrar", name: "lembrar" });
  const entrar = el("button", { class: "btn btn-primario btn-bloco", type: "submit", texto: "Entrar" });
  const formSenha = el(
    "form",
    { class: "auth-form", novalidate: true },
    email.bloco,
    senha.bloco,
    el("label", { class: "marcar", for: "lembrar" }, lembrar, "Manter conectado neste aparelho"),
    entrar,
  );
  const etapaSenha = el(
    "section",
    { class: "auth-cartao", "aria-labelledby": "titulo-entrar" },
    selo("cadeado"),
    el("h1", { class: "auth-titulo", id: "titulo-entrar", texto: "Entrar" }),
    el("p", { class: "auth-sub", texto: "Use seu e-mail e senha para ver suas finanças." }),
    avisoSenha,
    formSenha,
    el("p", { class: "auth-rodape" }, "Ainda não tem conta? ", el("a", { href: "#/cadastro", texto: "Criar conta" })),
  );

  const aviso2fa = el("div", { class: "mensagem", role: "alert" });
  const codigo = campo({ id: "codigo", rotulo: MODOS.app.rotulo, ajuda: MODOS.app.ajuda, class: "entrada entrada-codigo", maxlength: 32, required: true, spellcheck: "false", autocapitalize: "characters" });
  const confirmar = el("button", { class: "btn btn-primario btn-bloco", type: "submit", texto: "Confirmar e entrar" });
  const trocarModo = el("button", { class: "btn btn-texto auth-troca", type: "button" });
  const voltar = el("button", { class: "btn btn-texto auth-voltar", type: "button" }, icone("voltar", "ic-sm"), "Voltar");
  const form2fa = el("form", { class: "auth-form", novalidate: true }, codigo.bloco, confirmar);
  const instrucao2fa = el("p", { class: "auth-sub" });
  const titulo2fa = el("h1", { class: "auth-titulo", id: "titulo-2fa", texto: "Confirme que é você" });
  const etapa2fa = el(
    "section",
    { class: "auth-cartao", "aria-labelledby": "titulo-2fa", hidden: true },
    voltar,
    selo("escudo"),
    titulo2fa,
    instrucao2fa,
    aviso2fa,
    form2fa,
    trocarModo,
  );

  function aplicarModo(novo) {
    modo = novo;
    const m = MODOS[novo];
    codigo.bloco.querySelector("label").textContent = m.rotulo;
    codigo.bloco.querySelector(".campo-ajuda").textContent = m.ajuda;
    codigo.entrada.placeholder = m.placeholder;
    codigo.entrada.inputMode = m.inputmode;
    codigo.entrada.autocomplete = m.autocomplete;
    codigo.entrada.dataset.modo = novo;
    codigo.entrada.value = "";
    marcarErro(codigo, "");
    mensagem(aviso2fa, "erro", "");
    instrucao2fa.textContent = m.instrucao;
    trocarModo.textContent = m.troca;
  }

  function irParaSenha(tipo, texto) {
    etapa2fa.hidden = true;
    etapaSenha.hidden = false;
    mensagem(aviso2fa, "erro", "");
    mensagem(avisoSenha, tipo, texto);
    senha.entrada.value = "";
    senha.entrada.focus();
  }

  function irPara2fa() {
    inicioDesafio = Date.now();
    aplicarModo("app");
    mensagem(avisoSenha, "erro", "");
    etapaSenha.hidden = true;
    etapa2fa.hidden = false;
    codigo.entrada.focus();
  }

  function concluir(usuario) {
    definirUsuario(usuario);
    navegar(destino, { substituir: true });
  }

  function validarSenha() {
    const valorEmail = email.entrada.value.trim();
    marcarErro(email, !valorEmail ? "Informe seu e-mail." : !EMAIL_VALIDO.test(valorEmail) ? "Confira o e-mail: falta algo como @ ou o domínio." : "");
    marcarErro(senha, senha.entrada.value ? "" : "Informe sua senha.");
    const invalido = [email, senha].find((c) => c.entrada.getAttribute("aria-invalid") === "true");
    if (invalido) invalido.entrada.focus();
    return !invalido;
  }

  formSenha.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(avisoSenha, "erro", "");
    if (!validarSenha()) return;
    ocupado(entrar, true, "Entrando…");
    try {
      const resposta = await api.post("/auth/login", {
        email: email.entrada.value.trim(),
        senha: senha.entrada.value,
        lembrar: lembrar.checked,
      });
      if (resposta?.requer_2fa) irPara2fa();
      else concluir(resposta);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.status === 401) {
        mensagem(avisoSenha, "erro", erro.message);
        senha.entrada.value = "";
        senha.entrada.setAttribute("aria-invalid", "true");
        senha.entrada.focus();
      } else if (erro.status === 429) {
        mensagem(avisoSenha, "aviso", textoDeEspera(erro));
      } else {
        mensagem(avisoSenha, "erro", erro.message);
      }
    } finally {
      ocupado(entrar, false);
    }
  });

  for (const c of [email, senha]) c.entrada.addEventListener("input", () => marcarErro(c, ""));

  codigo.entrada.addEventListener("input", () => {
    marcarErro(codigo, "");
    if (modo === "app") codigo.entrada.value = codigo.entrada.value.replace(/\D/g, "").slice(0, 6);
  });

  form2fa.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(aviso2fa, "erro", "");
    const valor = codigo.entrada.value.trim();
    if (modo === "app" && valor.length !== 6) {
      marcarErro(codigo, "O código tem 6 números.");
      codigo.entrada.focus();
      return;
    }
    if (modo === "recuperacao" && valor.replace(/[\s-]/g, "").length < 16) {
      marcarErro(codigo, "Digite o código de recuperação completo, com 16 caracteres.");
      codigo.entrada.focus();
      return;
    }
    ocupado(confirmar, true, "Confirmando…");
    try {
      concluir(await api.post("/auth/login/2fa", { codigo: valor }));
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      const venceu = Date.now() - inicioDesafio >= DESAFIO_2FA_MIN * 60 * 1000;
      if (erro.status === 401 && venceu) {
        irParaSenha("aviso", `O tempo para digitar o código acabou. Entre de novo com sua senha.`);
      } else if (erro.status === 401) {
        mensagem(aviso2fa, "erro", erro.message);
        codigo.entrada.select();
        codigo.entrada.setAttribute("aria-invalid", "true");
        codigo.entrada.focus();
      } else if (erro.status === 429) {
        mensagem(aviso2fa, "aviso", textoDeEspera(erro));
      } else {
        mensagem(aviso2fa, "erro", erro.message);
      }
    } finally {
      ocupado(confirmar, false);
    }
  });

  trocarModo.addEventListener("click", () => {
    aplicarModo(modo === "app" ? "recuperacao" : "app");
    codigo.entrada.focus();
  });
  voltar.addEventListener("click", () => irParaSenha("erro", ""));

  raiz.append(telaAuth(etapaSenha, etapa2fa));
  aplicarModo("app");

  const pendente = mensagemParaProximaTela();
  if (pendente) mensagem(avisoSenha, pendente.tipo, pendente.texto);
  email.entrada.setAttribute("data-foco-inicial", "");

  if (location.hostname === "localhost") {
    import("../dev.js")
      .then(({ CONTA_TESTE }) => {
        if (!CONTA_TESTE?.email) return;
        const usar = el("button", { type: "button", class: "btn btn-texto", texto: "Usar conta de teste" });
        usar.addEventListener("click", () => {
          email.entrada.value = CONTA_TESTE.email;
          senha.entrada.value = CONTA_TESTE.senha;
          marcarErro(email, "");
          marcarErro(senha, "");
          entrar.focus();
        });
        formSenha.after(el("p", { class: "auth-rodape" }, usar, " (só em desenvolvimento)"));
      })
      .catch(() => {});
  }
}
