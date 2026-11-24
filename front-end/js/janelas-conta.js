import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { avisar } from "./avisos.js";
import { definirUsuario, encerrarLocalmente, usuarioAtual } from "./sessao.js";
import { desenharQr } from "./qr.js";
import { tremer } from "./movimento.js";

function janela({ titulo, aoFechar, pedirFechamento }) {
  const origemDoFoco = document.activeElement;
  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
  const corpo = el("div", { class: "jc-corpo" });
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const botoes = el("div", { class: "jc-botoes" });
  const formulario = el("form", { class: "jc-form", novalidate: true }, corpo, el("footer", { class: "jc-rodape" }, aviso, botoes));
  const dialogo = el(
    "dialog",
    { class: "jc-janela", "aria-labelledby": "jc-titulo" },
    el("header", { class: "jc-cabecalho" }, el("h2", { id: "jc-titulo", texto: titulo }), fechar),
    formulario,
  );
  const tentarFechar = async () => {
    if (!pedirFechamento || (await pedirFechamento())) dialogo.close();
  };
  fechar.addEventListener("click", tentarFechar);
  dialogo.addEventListener("cancel", (evento) => {
    evento.preventDefault();
    tentarFechar();
  });
  dialogo.addEventListener("close", () => {
    dialogo.remove();
    aoFechar?.();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
  });
  document.body.append(dialogo);
  dialogo.showModal();
  return {
    dialogo,
    formulario,
    corpo,
    botoes,
    erro: (texto, tipo = "erro") => mensagem(aviso, tipo, texto),
    fechar: () => dialogo.close(),
    titulo: (texto) => (dialogo.querySelector("#jc-titulo").textContent = texto),
  };
}

function campo({ id, rotulo, tipo = "text", autocomplete = "off", ajuda = null, ...extra }) {
  const erro = el("p", { class: "campo-erro", id: `${id}-erro` });
  const entrada = el("input", { class: "entrada", id, name: id, type: tipo, autocomplete, "aria-describedby": [ajuda ? `${id}-ajuda` : null, `${id}-erro`].filter(Boolean).join(" "), ...extra });
  const bloco = el("div", { class: "campo" }, el("label", { for: id, texto: rotulo }), entrada, ajuda ? el("p", { class: "campo-ajuda", id: `${id}-ajuda`, texto: ajuda }) : null, erro);
  const marcar = (texto) => {
    erro.textContent = texto;
    if (texto) entrada.setAttribute("aria-invalid", "true");
    else entrada.removeAttribute("aria-invalid");
  };
  entrada.addEventListener("input", () => marcar(""));
  return { bloco, entrada, marcar };
}

function campoSenha(id, rotulo = "Sua senha", autocomplete = "current-password") {
  return campo({ id, rotulo, tipo: "password", autocomplete, maxlength: 128 });
}

function campoCodigo(id, rotulo = "Código do app autenticador") {
  return campo({ id, rotulo, inputmode: "numeric", autocomplete: "one-time-code", maxlength: 32, spellcheck: "false", ajuda: "Os 6 dígitos do app, ou um código de recuperação." });
}

function botao(texto, classe, tipo = "button") {
  return el("button", { type: tipo, class: `btn ${classe}`, texto });
}

function tratarErro(j, erro, campoSenhaOuCodigo) {
  if (!(erro instanceof ErroApi)) throw erro;
  if (erro.status === 401 && campoSenhaOuCodigo) {
    campoSenhaOuCodigo.marcar(erro.message);
    campoSenhaOuCodigo.entrada.focus();
    tremer(campoSenhaOuCodigo.entrada);
    return;
  }
  j.erro(erro.message);
}

export function janelaNome({ aoSalvar }) {
  const j = janela({ titulo: "Seu nome" });
  const nome = campo({ id: "jc-nome", rotulo: "Nome", autocomplete: "name", maxlength: 100, value: usuarioAtual()?.nome ?? "" });
  const salvar = botao("Salvar", "btn-primario", "submit");
  j.corpo.append(el("p", { class: "jc-texto", texto: "É como a Balancia chama você nas telas e nos e-mails." }), nome.bloco);
  j.botoes.append(botao("Cancelar", "btn-secundario"), salvar);
  j.botoes.firstChild.addEventListener("click", j.fechar);
  nome.entrada.focus();
  nome.entrada.select();
  j.formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const valor = nome.entrada.value.trim();
    if (!valor) return nome.marcar("Escreva seu nome.");
    ocupado(salvar, true, "Salvando…");
    try {
      definirUsuario(await api.patch("/auth/me", { nome: valor }));
      j.fechar();
      avisar("Nome atualizado.");
      aoSalvar?.();
    } catch (erro) {
      ocupado(salvar, false);
      tratarErro(j, erro);
    }
  });
}

export function janelaEmail({ aoSalvar }) {
  const usuario = usuarioAtual();
  const j = janela({ titulo: "E-mail" });
  const estado = el(
    "div",
    { class: "jc-estado" },
    el("span", {}, el("b", { texto: usuario.email }), el("small", { texto: usuario.email_verificado ? "Confirmado" : "Ainda não confirmado" })),
  );
  if (!usuario.email_verificado) {
    const reenviar = botao("Reenviar confirmação", "btn-secundario");
    reenviar.addEventListener("click", async () => {
      ocupado(reenviar, true, "Enviando…");
      try {
        const resposta = await api.post("/auth/verificar-email/reenviar");
        j.erro(resposta.mensagem, "sucesso");
      } catch (erro) {
        tratarErro(j, erro);
      } finally {
        ocupado(reenviar, false);
      }
    });
    estado.append(reenviar);
  }
  const novo = campo({ id: "jc-email-novo", rotulo: "E-mail novo", tipo: "email", autocomplete: "email", maxlength: 254 });
  const senha = campoSenha("jc-email-senha");
  const codigo = usuario.dois_fatores ? campoCodigo("jc-email-codigo") : null;
  const enviar = botao("Enviar link de confirmação", "btn-primario", "submit");
  j.corpo.append(
    estado,
    el("h3", { class: "jc-subtitulo", texto: "Trocar de e-mail" }),
    el("p", { class: "jc-texto", texto: "Enviamos um link para o endereço novo. A troca só acontece depois que você clicar nele." }),
    novo.bloco,
    senha.bloco,
    codigo?.bloco,
  );
  j.botoes.append(enviar);
  j.formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    j.erro("");
    const email = novo.entrada.value.trim();
    if (!email.includes("@")) return novo.marcar("Escreva um e-mail válido."), novo.entrada.focus();
    if (!senha.entrada.value) return senha.marcar("Digite sua senha."), senha.entrada.focus();
    if (codigo && !codigo.entrada.value.trim()) return codigo.marcar("Digite o código."), codigo.entrada.focus();
    ocupado(enviar, true, "Enviando…");
    try {
      const corpo = { email_novo: email, senha: senha.entrada.value };
      if (codigo) corpo.codigo = codigo.entrada.value.trim();
      const resposta = await api.post("/auth/trocar-email", corpo);
      j.fechar();
      avisar(resposta.mensagem, { duracao: 9000 });
      aoSalvar?.();
    } catch (erro) {
      ocupado(enviar, false);
      if (erro instanceof ErroApi && erro.campos.email_novo) return novo.marcar("Confira o e-mail."), novo.entrada.focus();
      tratarErro(j, erro, codigo && erro.status === 401 ? codigo : senha);
    }
  });
  novo.entrada.focus();
}

export function janelaSenha() {
  const j = janela({ titulo: "Trocar senha" });
  const atual = campoSenha("jc-senha-atual", "Senha atual");
  const nova = campo({ id: "jc-senha-nova", rotulo: "Senha nova", tipo: "password", autocomplete: "new-password", minlength: 8, maxlength: 128, ajuda: "Pelo menos 8 caracteres." });
  const repetir = campo({ id: "jc-senha-repetir", rotulo: "Repita a senha nova", tipo: "password", autocomplete: "new-password", maxlength: 128 });
  const salvar = botao("Trocar senha", "btn-primario", "submit");
  j.corpo.append(el("p", { class: "jc-texto", texto: "Depois da troca, as outras sessões abertas são encerradas. Esta continua." }), atual.bloco, nova.bloco, repetir.bloco);
  j.botoes.append(salvar);
  atual.entrada.focus();
  j.formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    j.erro("");
    if (!atual.entrada.value) return atual.marcar("Digite a senha atual."), atual.entrada.focus();
    if (nova.entrada.value.length < 8) return nova.marcar("A senha nova precisa de pelo menos 8 caracteres."), nova.entrada.focus();
    if (repetir.entrada.value !== nova.entrada.value) return repetir.marcar("As senhas não são iguais."), repetir.entrada.focus();
    ocupado(salvar, true, "Trocando…");
    try {
      await api.post("/auth/trocar-senha", { senha_atual: atual.entrada.value, senha_nova: nova.entrada.value });
      j.fechar();
      avisar("Senha alterada. As outras sessões foram encerradas.");
    } catch (erro) {
      ocupado(salvar, false);
      tratarErro(j, erro, atual);
    }
  });
}

function mostrarCodigos(j, codigos, aoConcluir) {
  j.titulo("Códigos de recuperação");
  const lista = el("ol", { class: "jc-codigos" }, codigos.map((c) => el("li", { texto: c })));
  const copiar = botao("Copiar", "btn-secundario");
  copiar.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(codigos.join("\n"));
      copiar.textContent = "Copiados";
    } catch {
      j.erro("Não foi possível copiar. Selecione os códigos e copie à mão.");
    }
  });
  const baixar = botao("Baixar .txt", "btn-secundario");
  baixar.addEventListener("click", () => {
    const arquivo = new Blob([`Códigos de recuperação da Balancia\nCada código funciona uma vez.\n\n${codigos.join("\n")}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(arquivo);
    const link = el("a", { href: url, download: "financas-codigos-de-recuperacao.txt" });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  const guardei = el("input", { type: "checkbox", id: "jc-guardei", name: "guardei" });
  const concluir = botao("Concluir", "btn-primario", "submit");
  concluir.disabled = true;
  guardei.addEventListener("change", () => (concluir.disabled = !guardei.checked));
  j.corpo.replaceChildren(
    el("p", { class: "jc-texto", texto: "Se você perder o celular, cada um destes códigos entra no lugar do código do app, uma única vez. Guarde num lugar seguro: eles não aparecem de novo." }),
    lista,
    el("div", { class: "jc-acoes" }, copiar, baixar),
    el("label", { class: "marcar", for: "jc-guardei" }, guardei, "Guardei os códigos"),
  );
  j.erro("");
  j.botoes.replaceChildren(concluir);
  j.formulario.onsubmit = (evento) => {
    evento.preventDefault();
    j.fechar();
    aoConcluir?.();
  };
  copiar.focus();
}

export function janelaDoisFatores({ aoMudar }) {
  const ligado = usuarioAtual().dois_fatores;
  let mostrandoCodigos = false;
  const j = janela({
    titulo: "Verificação em duas etapas",
    pedirFechamento: async () => !mostrandoCodigos || j.formulario.querySelector("#jc-guardei")?.checked || false,
  });
  const atualizar = async () => {
    definirUsuario(await api.get("/auth/me"));
    aoMudar?.();
  };

  if (!ligado) {
    const comecar = botao("Começar", "btn-primario", "submit");
    j.corpo.append(
      el("p", { class: "jc-texto", texto: "Além da senha, o login vai pedir um código de 6 dígitos que muda a cada 30 segundos, gerado num app autenticador no seu celular (Google Authenticator, Microsoft Authenticator, Authy, 1Password…)." }),
      el("p", { class: "jc-texto", texto: "Assim, mesmo que alguém descubra sua senha, não consegue entrar sem o seu celular." }),
    );
    j.botoes.append(comecar);
    comecar.focus();
    j.formulario.onsubmit = async (evento) => {
      evento.preventDefault();
      ocupado(comecar, true, "Preparando…");
      try {
        const { segredo, uri } = await api.post("/auth/2fa/iniciar");
        const qr = await desenharQr(uri, "QR code para o app autenticador").catch(() => null);
        const codigo = campo({ id: "jc-2fa-codigo", rotulo: "Código de 6 dígitos", inputmode: "numeric", autocomplete: "one-time-code", maxlength: 6, spellcheck: "false" });
        const senha = campoSenha("jc-2fa-senha");
        const ativar = botao("Ativar", "btn-primario", "submit");
        j.corpo.replaceChildren(
          el(
            "div",
            { class: "jc-qr" },
            qr ? el("div", { class: "jc-qr-imagem" }, qr) : el("p", { class: "jc-texto", texto: "Não foi possível mostrar o QR code. Use a chave abaixo." }),
            el(
              "div",
              {},
              el("p", { class: "jc-passo", texto: "1. No app autenticador, leia o QR code" }),
              el("p", { class: "jc-texto", texto: "Ou digite esta chave:" }),
              el("code", { class: "jc-chave", texto: segredo.replace(/(.{4})/g, "$1 ").trim() }),
            ),
          ),
          el("p", { class: "jc-passo", texto: "2. Digite o código que o app mostrar e sua senha" }),
          el("div", { class: "jc-linha" }, codigo.bloco, senha.bloco),
        );
        j.botoes.replaceChildren(ativar);
        codigo.entrada.focus();
        j.formulario.onsubmit = async (e) => {
          e.preventDefault();
          j.erro("");
          if (!/^\d{6}$/.test(codigo.entrada.value.trim())) return codigo.marcar("Digite os 6 dígitos do app."), codigo.entrada.focus();
          if (!senha.entrada.value) return senha.marcar("Digite sua senha."), senha.entrada.focus();
          ocupado(ativar, true, "Ativando…");
          try {
            const { codigos } = await api.post("/auth/2fa/ativar", { senha: senha.entrada.value, codigo: codigo.entrada.value.trim() });
            mostrandoCodigos = true;
            await atualizar();
            mostrarCodigos(j, codigos, () => avisar("Verificação em duas etapas ativada."));
          } catch (erro) {
            ocupado(ativar, false);
            tratarErro(j, erro, codigo);
          }
        };
      } catch (erro) {
        ocupado(comecar, false);
        tratarErro(j, erro);
      }
    };
    return;
  }

  const codigo = campoCodigo("jc-2fa-codigo");
  const senha = campoSenha("jc-2fa-senha");
  const novos = botao("Gerar novos códigos", "btn-secundario", "submit");
  const desativar = botao("Desativar", "btn-perigo", "submit");
  j.corpo.append(
    el("div", { class: "jc-estado" }, el("span", {}, el("b", { texto: "Ligada" }), el("small", { texto: "O login pede o código do app autenticador." }))),
    el("p", { class: "jc-texto", texto: "Para gerar novos códigos de recuperação ou desativar, confirme com sua senha e um código." }),
    senha.bloco,
    codigo.bloco,
  );
  j.botoes.append(novos, desativar);
  senha.entrada.focus();
  j.formulario.onsubmit = async (evento) => {
    evento.preventDefault();
    j.erro("");
    const acao = evento.submitter === desativar ? "desativar" : "codigos-recuperacao";
    if (!senha.entrada.value) return senha.marcar("Digite sua senha."), senha.entrada.focus();
    if (!codigo.entrada.value.trim()) return codigo.marcar("Digite o código."), codigo.entrada.focus();
    const alvo = acao === "desativar" ? desativar : novos;
    ocupado(alvo, true, acao === "desativar" ? "Desativando…" : "Gerando…");
    try {
      const resposta = await api.post(`/auth/2fa/${acao}`, { senha: senha.entrada.value, codigo: codigo.entrada.value.trim() });
      if (acao === "desativar") {
        j.fechar();
        await atualizar();
        avisar("Verificação em duas etapas desativada.");
      } else {
        mostrandoCodigos = true;
        mostrarCodigos(j, resposta.codigos, () => avisar("Novos códigos gerados. Os antigos deixaram de valer."));
      }
    } catch (erro) {
      ocupado(alvo, false);
      tratarErro(j, erro, codigo);
    }
  };
}

const CIDADES = { "Sao Paulo": "São Paulo", Cuiaba: "Cuiabá", Belem: "Belém", Maceio: "Maceió", Araguaina: "Araguaína", Santarem: "Santarém", Noronha: "Fernando de Noronha", Eirunepe: "Eirunepé" };

function nomeDoFuso(fuso) {
  const bruto = fuso.split("/").pop().replaceAll("_", " ");
  const cidade = CIDADES[bruto] ?? bruto;
  try {
    const partes = new Intl.DateTimeFormat("pt-BR", { timeZone: fuso, timeZoneName: "shortOffset" }).formatToParts(new Date());
    const deslocamento = partes.find((p) => p.type === "timeZoneName")?.value.replace("GMT", "UTC") ?? "";
    return `${cidade} (${deslocamento === "UTC" ? "UTC+0" : deslocamento})`;
  } catch {
    return cidade;
  }
}

export { nomeDoFuso };

export function janelaFuso({ aoSalvar }) {
  const j = janela({ titulo: "Fuso horário" });
  const atual = usuarioAtual().fuso;
  const fusos = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [atual];
  if (!fusos.includes(atual)) fusos.unshift(atual);
  const select = el("select", { class: "entrada", id: "jc-fuso", name: "fuso" }, fusos.map((f) => el("option", { value: f, texto: `${nomeDoFuso(f)} ${f.includes("/") ? `– ${f.split("/")[0]}` : ""}`.trim() })));
  select.value = atual;
  const salvar = botao("Salvar", "btn-primario", "submit");
  j.corpo.append(
    el("p", { class: "jc-texto", texto: "Define o que conta como hoje, o mês das transações e a hora dos lembretes." }),
    el("div", { class: "campo" }, el("label", { for: "jc-fuso", texto: "Fuso" }), select),
  );
  j.botoes.append(salvar);
  select.focus();
  j.formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    ocupado(salvar, true, "Salvando…");
    try {
      definirUsuario(await api.patch("/auth/me", { fuso: select.value }));
      j.fechar();
      avisar("Fuso horário atualizado.");
      aoSalvar?.();
    } catch (erro) {
      ocupado(salvar, false);
      tratarErro(j, erro);
    }
  });
}

export function janelaExcluir({ aoExcluir }) {
  const j = janela({ titulo: "Excluir conta" });
  const senha = campoSenha("jc-excluir-senha");
  const excluir = botao("Excluir minha conta", "btn-perigo", "submit");
  j.corpo.append(
    el("div", { class: "jc-alerta" }, icone("alerta", "ic-sm"), el("p", { texto: "Isso apaga para sempre suas transações, contas, categorias e preferências. Não dá para desfazer." })),
    el("p", { class: "jc-texto", texto: "Se quiser guardar seus dados, exporte as transações em CSV antes, na tela de Transações." }),
    senha.bloco,
  );
  j.botoes.append(botao("Cancelar", "btn-secundario"), excluir);
  j.botoes.firstChild.addEventListener("click", j.fechar);
  senha.entrada.focus();
  j.formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    j.erro("");
    if (!senha.entrada.value) return senha.marcar("Digite sua senha para confirmar."), senha.entrada.focus();
    ocupado(excluir, true, "Excluindo…");
    try {
      await api.post("/auth/excluir-conta", { senha: senha.entrada.value });
      encerrarLocalmente();
      j.fechar();
      aoExcluir?.();
    } catch (erro) {
      ocupado(excluir, false);
      tratarErro(j, erro, senha);
    }
  });
}
