import { el, icone } from "../dom.js";
import { CARTOES, LARGURAS, PADRAO, copiaDoPadrao } from "./preferencias.js";

const ROTULO_LARGURA = { estreito: "Coluna estreita", largo: "Coluna larga", inteiro: "Linha inteira" };
const MARGEM_ROLAGEM = 72;
const VELOCIDADE_ROLAGEM = 14;

export function criarEdicao({ grade, adicionar, titulos, aplicarLayout, alturaEmLinhas, salvar, anunciar, preferencias }) {
  let rascunho = null;
  const desktop = matchMedia("(min-width: 900px)");
  const titulo = (id) => titulos[id];
  const posicao = (id) => rascunho.cartoes.findIndex((c) => c.id === id);
  const secaoDe = (id) => grade.querySelector(`.cartao[data-cartao="${id}"]`);

  function atualizar() {
    aplicarLayout(rascunho.cartoes);
    rascunho.cartoes.forEach(({ id, largura }, i) => {
      const secao = secaoDe(id);
      if (!secao) return;
      secao.querySelector(".subir").disabled = i === 0;
      secao.querySelector(".descer").disabled = i === rascunho.cartoes.length - 1;
      secao.querySelector(".cartao-ed select").value = largura;
    });
    for (const conteudo of grade.querySelectorAll(".cartao-conteudo")) conteudo.inert = true;
    desenharAdicionar();
  }

  function focar(id, seletor) {
    const secao = secaoDe(id);
    const alvo = secao?.querySelector(`${seletor}:not(:disabled)`) ?? secao?.querySelector(".alca");
    alvo?.focus();
  }

  function mover(id, passo, seletor) {
    const i = posicao(id);
    const j = i + passo;
    if (j < 0 || j >= rascunho.cartoes.length) return;
    [rascunho.cartoes[i], rascunho.cartoes[j]] = [rascunho.cartoes[j], rascunho.cartoes[i]];
    atualizar();
    focar(id, seletor);
    anunciar(`${titulo(id)} na posição ${j + 1} de ${rascunho.cartoes.length}.`);
  }

  function barra(id) {
    const alca = el("button", { type: "button", class: "alca", "aria-label": `Arrastar ${titulo(id)}`, title: "Arraste para mover" }, icone("arrastar"));
    alca.addEventListener("pointerdown", (evento) => iniciarArraste(evento, id));
    alca.addEventListener("keydown", (evento) => {
      if (evento.key === "ArrowUp" || evento.key === "ArrowDown") {
        evento.preventDefault();
        mover(id, evento.key === "ArrowUp" ? -1 : 1, ".alca");
      }
    });
    const subir = el("button", { type: "button", class: "subir", "aria-label": `Subir ${titulo(id)}`, title: "Subir" }, icone("cima"));
    subir.addEventListener("click", () => mover(id, -1, ".subir"));
    const descer = el("button", { type: "button", class: "descer", "aria-label": `Descer ${titulo(id)}`, title: "Descer" }, icone("baixo"));
    descer.addEventListener("click", () => mover(id, 1, ".descer"));
    const largura = el("select", { "aria-label": `Largura de ${titulo(id)}` }, LARGURAS.map((l) => el("option", { value: l, texto: ROTULO_LARGURA[l] })));
    largura.addEventListener("change", () => {
      rascunho.cartoes[posicao(id)].largura = largura.value;
      atualizar();
      anunciar(`${titulo(id)}: ${ROTULO_LARGURA[largura.value].toLowerCase()}.`);
    });
    const remover = el("button", { type: "button", class: "remover", "aria-label": `Remover ${titulo(id)}`, title: "Remover do painel" }, icone("fechar"));
    remover.addEventListener("click", () => {
      const i = posicao(id);
      rascunho.cartoes.splice(i, 1);
      atualizar();
      anunciar(`${titulo(id)} removido. Você pode adicionar de volta em Adicionar cartão.`);
      const vizinho = rascunho.cartoes[Math.min(i, rascunho.cartoes.length - 1)];
      if (vizinho) focar(vizinho.id, ".alca");
      else adicionar.querySelector("button")?.focus();
    });
    return el(
      "div",
      { class: "cartao-ed", role: "group", "aria-label": `Organizar ${titulo(id)}` },
      alca,
      el("span", { class: "cartao-ed-titulo", texto: titulo(id), "aria-hidden": "true" }),
      subir,
      descer,
      largura,
      remover,
    );
  }

  function desenharAdicionar() {
    adicionar.replaceChildren(el("h2", { id: "titulo-adicionar", texto: "Adicionar cartão" }));
    adicionar.setAttribute("aria-labelledby", "titulo-adicionar");
    const fora = CARTOES.filter((id) => posicao(id) === -1);
    if (fora.length) {
      const lista = el("ul");
      for (const id of fora) {
        const botao = el("button", { type: "button", class: "btn btn-secundario" }, icone("mais", "ic-sm"), titulo(id));
        botao.addEventListener("click", () => {
          const largura = PADRAO.cartoes.find((c) => c.id === id)?.largura ?? (id === "meses" || id === "transacoes" ? "largo" : "estreito");
          rascunho.cartoes.push({ id, largura });
          atualizar();
          anunciar(`${titulo(id)} adicionado no fim do painel.`);
          focar(id, ".alca");
        });
        lista.append(el("li", {}, botao));
      }
      adicionar.append(lista);
    } else {
      adicionar.append(el("p", { texto: "Todos os cartões já estão no painel." }));
    }
    const padrao = el("button", { type: "button", class: "btn btn-texto", texto: "Voltar ao painel padrão" });
    padrao.addEventListener("click", () => {
      const atual = rascunho;
      rascunho = { ...atual, ...copiaDoPadrao() };
      atualizar();
      anunciar("Painel padrão restaurado. Toque em Concluir para salvar.");
    });
    adicionar.append(el("div", { class: "adicionar-rodape" }, padrao));
  }

  function larguraPeloPonteiro(x, original) {
    if (!desktop.matches || original === "inteiro") return original;
    const caixa = grade.getBoundingClientRect();
    const primeira = parseFloat(getComputedStyle(grade).gridTemplateColumns.split(" ")[0]);
    return x < caixa.left + primeira + 9 ? "estreito" : "largo";
  }

  function iniciarArraste(evento, id) {
    if (evento.pointerType === "mouse" && evento.button !== 0) return;
    evento.preventDefault();
    const alca = evento.currentTarget;
    const secao = secaoDe(id);
    const original = rascunho.cartoes[posicao(id)].largura;
    let largura = original;
    const caixa = secao.getBoundingClientRect();
    const deslocamento = { x: evento.clientX - caixa.left, y: evento.clientY - caixa.top };
    let ponteiro = { x: evento.clientX, y: evento.clientY };

    const marcador = el("div", { class: `cartao-marcador t-${largura}`, "aria-hidden": "true" });
    marcador.style.height = `${caixa.height}px`;
    if (desktop.matches) marcador.style.gridRowEnd = `span ${alturaEmLinhas(caixa.height)}`;
    secao.before(marcador);
    secao.classList.add("arrastando");
    secao.inert = true;
    Object.assign(secao.style, { width: `${caixa.width}px`, height: `${caixa.height}px`, left: `${caixa.left}px`, top: `${caixa.top}px` });
    document.body.classList.add("arrastando-cartao");
    alca.setPointerCapture(evento.pointerId);

    function posicionarCartao() {
      secao.style.left = `${ponteiro.x - deslocamento.x}px`;
      secao.style.top = `${ponteiro.y - deslocamento.y}px`;
    }

    function posicionarMarcador() {
      largura = larguraPeloPonteiro(ponteiro.x, original);
      marcador.className = `cartao-marcador t-${largura}`;
      const candidatos = [...grade.querySelectorAll(".cartao:not(.arrastando)")].filter(
        (outro) => !desktop.matches || largura === "inteiro" || outro.classList.contains(`t-${largura}`) || outro.classList.contains("t-inteiro"),
      );
      const alvo = candidatos.find((outro) => {
        const r = outro.getBoundingClientRect();
        return ponteiro.y < r.top + r.height / 2;
      });
      if (alvo) {
        if (alvo.previousElementSibling !== marcador) alvo.before(marcador);
      } else if (candidatos.length) {
        const ultimo = candidatos.at(-1);
        if (ultimo.nextElementSibling !== marcador) ultimo.after(marcador);
      }
    }

    let quadro = 0;
    function rolar() {
      const passo = ponteiro.y < MARGEM_ROLAGEM ? -VELOCIDADE_ROLAGEM : ponteiro.y > innerHeight - MARGEM_ROLAGEM ? VELOCIDADE_ROLAGEM : 0;
      if (passo) {
        scrollBy(0, passo);
        posicionarMarcador();
      }
      quadro = requestAnimationFrame(rolar);
    }
    quadro = requestAnimationFrame(rolar);

    function aoMover(e) {
      ponteiro = { x: e.clientX, y: e.clientY };
      posicionarCartao();
      posicionarMarcador();
    }

    function terminar(cancelado) {
      cancelAnimationFrame(quadro);
      alca.removeEventListener("pointermove", aoMover);
      alca.removeEventListener("pointerup", aoSoltar);
      alca.removeEventListener("pointercancel", aoCancelar);
      document.removeEventListener("keydown", aoTeclar, true);
      document.body.classList.remove("arrastando-cartao");
      secao.classList.remove("arrastando");
      secao.inert = false;
      for (const prop of ["width", "height", "left", "top"]) secao.style[prop] = "";
      if (cancelado) {
        marcador.remove();
        anunciar("Movimento cancelado.");
      } else {
        marcador.replaceWith(secao);
        const ordem = [...grade.querySelectorAll(".cartao")].map((s) => s.dataset.cartao);
        const larguras = Object.fromEntries(rascunho.cartoes.map((c) => [c.id, c.largura]));
        larguras[id] = largura;
        rascunho.cartoes = ordem.map((cid) => ({ id: cid, largura: larguras[cid] }));
        atualizar();
        const coluna = desktop.matches && largura !== original ? `, agora na ${ROTULO_LARGURA[largura].toLowerCase()}` : "";
        anunciar(`${titulo(id)} na posição ${posicao(id) + 1} de ${rascunho.cartoes.length}${coluna}.`);
      }
      alca.focus();
    }
    const aoSoltar = () => terminar(false);
    const aoCancelar = () => terminar(true);
    function aoTeclar(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        terminar(true);
      }
    }
    alca.addEventListener("pointermove", aoMover);
    alca.addEventListener("pointerup", aoSoltar);
    alca.addEventListener("pointercancel", aoCancelar);
    document.addEventListener("keydown", aoTeclar, true);
  }

  return {
    barra,
    editando: () => rascunho !== null,
    alterou: () => rascunho !== null && JSON.stringify(rascunho) !== JSON.stringify(preferencias()),
    entrar() {
      rascunho = structuredClone(preferencias());
      grade.classList.add("editando");
      atualizar();
      anunciar("Personalizando o painel. Arraste os cartões pela alça ou use os botões de subir e descer.");
      grade.querySelector(".alca")?.focus();
    },
    acompanhar(parcial) {
      if (rascunho) Object.assign(rascunho, parcial);
    },
    cancelar() {
      rascunho = null;
      grade.classList.remove("editando");
      aplicarLayout(preferencias().cartoes);
      for (const conteudo of grade.querySelectorAll(".cartao-conteudo")) conteudo.inert = false;
      anunciar("Alterações descartadas.");
    },
    async concluir() {
      await salvar(rascunho);
      rascunho = null;
      grade.classList.remove("editando");
      aplicarLayout(preferencias().cartoes);
      for (const conteudo of grade.querySelectorAll(".cartao-conteudo")) conteudo.inert = false;
      anunciar("Painel salvo.");
    },
  };
}
