import { api, ErroApi } from "../api.js";
import { el, icone } from "../dom.js";
import { avisar } from "../avisos.js";
import { definirUsuario, usuarioAtual } from "../sessao.js";
import { sairDaConta } from "../app.js";
import { animacoesLigadas, definirAnimacoes } from "../movimento.js";
import { janelaDoisFatores, janelaEmail, janelaExcluir, janelaFuso, janelaNome, janelaSenha, nomeDoFuso } from "../janelas-conta.js";

const DIAS = [0, 1, 2, 3, 5, 7];
const EXPLICACOES = {
  antes: "Um e-mail chega alguns dias antes de cada conta vencer, a partir das 8h no seu fuso. Vale para as contas com o sino ligado na tela Contas.",
  dia: "No dia do vencimento, um e-mail lista as contas que vencem hoje e ainda não foram pagas.",
  atraso: "No dia seguinte ao vencimento, se a conta não foi marcada como paga, você recebe um aviso.",
  animacoes: "Liga ou desliga os movimentos do site: a logo da abertura, números contando, gráficos crescendo, janelas e avisos deslizando. Vale só neste aparelho e navegador.",
  resumo: "Nos primeiros dias de cada mês, um e-mail com o total de gastos e ganhos do mês anterior, as maiores categorias e as contas do mês. Meses sem transações não geram e-mail.",
};

export async function montar(raiz, { navegar }) {
  let dicaAberta = null;

  function fecharDica() {
    if (!dicaAberta) return;
    dicaAberta.setAttribute("aria-expanded", "false");
    dicaAberta = null;
  }

  function dica(id, assunto) {
    const balao = el("span", { class: "info-balao", id: `dica-${id}`, role: "tooltip", texto: EXPLICACOES[id] });
    const botao = el("button", { type: "button", class: "info-botao", "aria-label": `Como funciona: ${assunto}`, "aria-describedby": `dica-${id}`, "aria-expanded": "false" }, icone("info", "ic-sm"));
    botao.addEventListener("click", (evento) => {
      evento.stopPropagation();
      const abrir = botao.getAttribute("aria-expanded") !== "true";
      fecharDica();
      if (abrir) {
        botao.setAttribute("aria-expanded", "true");
        dicaAberta = botao;
      }
    });
    return el("span", { class: "info" }, botao, balao);
  }

  async function salvarPreferencia(parcial, desfazer) {
    try {
      definirUsuario(await api.patch("/auth/me", parcial));
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      desfazer();
      avisar(erro.message, { tipo: "erro" });
    }
  }

  function interruptor(id, rotulo, chave) {
    const caixa = el("input", { type: "checkbox", role: "switch", id: `cf-${id}`, name: chave });
    caixa.checked = Boolean(usuarioAtual()[chave]);
    caixa.addEventListener("change", () => salvarPreferencia({ [chave]: caixa.checked }, () => (caixa.checked = !caixa.checked)));
    return el(
      "div",
      { class: "cf-item cf-item-chave" },
      el("span", { class: "cf-ic", "aria-hidden": "true" }, icone(id === "resumo" ? "painel" : id === "atraso" ? "alerta" : "contas")),
      el("span", { class: "cf-texto" }, el("label", { for: `cf-${id}`, class: "cf-titulo", texto: rotulo }), dica(id, rotulo)),
      el("label", { class: "cf-chave", for: `cf-${id}` }, caixa, el("span", { class: "interruptor", "aria-hidden": "true" })),
    );
  }

  function interruptorAnimacoes() {
    const caixa = el("input", { type: "checkbox", role: "switch", id: "cf-animacoes", name: "animacoes" });
    caixa.checked = animacoesLigadas();
    caixa.addEventListener("change", () => {
      definirAnimacoes(caixa.checked);
      avisar(caixa.checked ? "Animações ligadas neste aparelho." : "Animações desligadas neste aparelho.");
    });
    return el(
      "div",
      { class: "cf-item cf-item-chave" },
      el("span", { class: "cf-ic", "aria-hidden": "true" }, icone("ajustes")),
      el("span", { class: "cf-texto" }, el("label", { for: "cf-animacoes", class: "cf-titulo", texto: "Animações" }), dica("animacoes", "Animações")),
      el("label", { class: "cf-chave", for: "cf-animacoes" }, caixa, el("span", { class: "interruptor", "aria-hidden": "true" })),
    );
  }

  function diasAntes() {
    const grupo = el("div", { class: "cf-dias", role: "radiogroup", "aria-labelledby": "cf-titulo-antes" });
    const desenhar = () => {
      const atual = usuarioAtual().lembrete_dias_antes;
      const opcoes = [...new Set([...DIAS, atual])].sort((x, y) => x - y);
      grupo.replaceChildren(
        ...opcoes.map((dias) => {
          const b = el("button", { type: "button", role: "radio", "aria-checked": String(atual === dias), tabindex: atual === dias ? "0" : "-1", texto: dias === 0 ? "Não" : String(dias) });
          b.setAttribute("aria-label", dias === 0 ? "Não avisar antes" : dias === 1 ? "1 dia antes" : `${dias} dias antes`);
          b.addEventListener("click", () => escolher(dias));
          b.addEventListener("keydown", (evento) => {
            const passo = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[evento.key];
            if (!passo) return;
            evento.preventDefault();
            const proximo = opcoes[(opcoes.indexOf(dias) + passo + opcoes.length) % opcoes.length];
            escolher(proximo);
          });
          return b;
        }),
      );
    };
    const escolher = (dias) => {
      const anterior = usuarioAtual().lembrete_dias_antes;
      if (anterior === dias) return;
      definirUsuario({ ...usuarioAtual(), lembrete_dias_antes: dias });
      desenhar();
      grupo.querySelector('[aria-checked="true"]')?.focus();
      salvarPreferencia({ lembrete_dias_antes: dias }, () => {
        definirUsuario({ ...usuarioAtual(), lembrete_dias_antes: anterior });
        desenhar();
      });
    };
    desenhar();
    return el(
      "div",
      { class: "cf-item cf-item-dias" },
      el("span", { class: "cf-ic", "aria-hidden": "true" }, icone("sino")),
      el("span", { class: "cf-texto" }, el("span", { class: "cf-titulo", id: "cf-titulo-antes", texto: "Avisar antes do vencimento" }), dica("antes", "Avisar antes do vencimento")),
      grupo,
    );
  }

  function linha({ ic, titulo, descricao, valor, aoClicar, href, perigo = false }) {
    const conteudo = [
      el("span", { class: "cf-ic", "aria-hidden": "true" }, icone(ic)),
      el("span", { class: "cf-texto" }, el("span", { class: "cf-titulo", texto: titulo }), descricao ? el("small", { texto: descricao }) : null),
      valor ? el("span", { class: "cf-valor", texto: valor }) : el("span"),
      el("span", { class: "cf-seta", "aria-hidden": "true" }, icone("proximo", "ic-sm")),
    ];
    const item = href ? el("a", { class: `cf-item cf-linha${perigo ? " perigo" : ""}`, href }, ...conteudo) : el("button", { type: "button", class: `cf-item cf-linha${perigo ? " perigo" : ""}` }, ...conteudo);
    if (aoClicar) item.addEventListener("click", aoClicar);
    return item;
  }

  function secao(titulo, ...itens) {
    const id = `cf-secao-${titulo.normalize("NFD").replace(/[^a-z]/gi, "").toLowerCase()}`;
    return el("section", { class: "cf-secao", "aria-labelledby": id }, el("h2", { id, texto: titulo }), el("div", { class: "cf-caixa" }, ...itens));
  }

  function desenhar() {
    const u = usuarioAtual();
    const selo = u.email_verificado ? el("span", { class: "cf-selo ok", texto: "confirmado" }) : el("span", { class: "cf-selo", texto: "não confirmado" });
    const avisoEmail = u.email_verificado
      ? null
      : el("p", { class: "cf-aviso" }, icone("alerta", "ic-sm"), el("span", { texto: "Confirme seu e-mail para receber estes avisos. O link está na sua caixa de entrada; dá para reenviar em E-mail." }));
    raiz.replaceChildren(
      el("h1", { class: "cf-h1", texto: "Conta" }),
      el(
        "section",
        { class: "cf-perfil", "aria-label": "Perfil" },
        el("span", { class: "cf-avatar", "aria-hidden": "true", texto: (u.nome.trim()[0] ?? "?").toUpperCase() }),
        el("div", { class: "cf-perfil-texto" }, el("b", { texto: u.nome }), el("span", {}, el("span", { class: "cf-email", texto: u.email }), selo)),
      ),
      secao(
        "Perfil",
        linha({ ic: "conta", titulo: "Nome", descricao: "Como o Finanças chama você", valor: u.nome, aoClicar: () => janelaNome({ aoSalvar: desenhar }) }),
        linha({ ic: "info", titulo: "E-mail", descricao: "Para entrar e receber avisos", valor: u.email, aoClicar: () => janelaEmail({ aoSalvar: desenhar }) }),
      ),
      secao(
        "Segurança",
        linha({ ic: "cadeado", titulo: "Senha", descricao: "Trocar encerra as outras sessões", valor: "Trocar", aoClicar: () => janelaSenha() }),
        linha({ ic: "escudo", titulo: "Verificação em duas etapas", descricao: "Código do app autenticador ao entrar", valor: u.dois_fatores ? "Ligada" : "Desligada", aoClicar: () => janelaDoisFatores({ aoMudar: desenhar }) }),
      ),
      el(
        "section",
        { class: "cf-secao", "aria-labelledby": "cf-secao-avisos" },
        el("h2", { id: "cf-secao-avisos", texto: "Avisos por e-mail" }),
        avisoEmail,
        el(
          "div",
          { class: "cf-caixa" },
          diasAntes(),
          interruptor("dia", "No dia do vencimento", "lembrete_no_dia"),
          interruptor("atraso", "Se atrasar", "lembrete_atraso"),
          interruptor("resumo", "Resumo do mês", "resumo_mensal"),
          linha({ ic: "contas", titulo: "Fuso horário", descricao: "Hora dos avisos e virada do mês", valor: nomeDoFuso(u.fuso), aoClicar: () => janelaFuso({ aoSalvar: desenhar }) }),
        ),
      ),
      secao("Neste aparelho", interruptorAnimacoes()),
      secao(
        "Mais",
        linha({ ic: "categorias", titulo: "Categorias", descricao: "Criar e editar as suas", href: "#/categorias" }),
        linha({ ic: "sair", titulo: "Sair", aoClicar: sairDaConta }),
        linha({ ic: "erro", titulo: "Excluir conta", descricao: "Apaga tudo, sem volta", perigo: true, aoClicar: () => janelaExcluir({ aoExcluir: () => { avisar("Sua conta foi excluída."); navegar("/entrar", { substituir: true, forcar: true }); } }) }),
      ),
      el(
        "footer",
        { class: "cf-creditos" },
        el("p", {}, "Ícones de marcas: ", el("a", { href: "https://simpleicons.org", target: "_blank", rel: "noopener", texto: "Simple Icons" }), " (CC0) e ", el("a", { href: "https://github.com/Arcticons-Team/Arcticons", target: "_blank", rel: "noopener", texto: "Arcticons" }), ", de Donnnno e colaboradores (", el("a", { href: "https://creativecommons.org/licenses/by-sa/4.0/", target: "_blank", rel: "noopener", texto: "CC BY-SA 4.0" }), "). As marcas pertencem às suas empresas."),
        el("p", {}, "QR code: ", el("a", { href: "https://github.com/kazuhikoarase/qrcode-generator", target: "_blank", rel: "noopener", texto: "qrcode-generator" }), ", de Kazuhiko Arase (MIT). QR Code é marca registrada da DENSO WAVE."),
      ),
    );
  }

  function aoClicarFora(evento) {
    if (dicaAberta && !evento.target.closest(".info")) fecharDica();
  }
  function aoTeclar(evento) {
    if (evento.key === "Escape" && dicaAberta) {
      const botao = dicaAberta;
      fecharDica();
      botao.focus();
    }
  }
  document.addEventListener("click", aoClicarFora);
  document.addEventListener("keydown", aoTeclar);

  desenhar();

  return () => {
    document.removeEventListener("click", aoClicarFora);
    document.removeEventListener("keydown", aoTeclar);
  };
}
