import { api, ErroApi } from "../api.js";
import { el, icone, mensagem, ocupado } from "../dom.js";
import { carregarCategorias, corDaCategoria } from "../categorias.js";
import { abrirImportacao, esquecerPrevia, pedirPrevia, previaGuardada } from "../importacao.js";
import { criarSugestor } from "../sugestao-categoria.js";
import { moedaComSinal } from "../formatos.js";
import { confirmar } from "../confirmar.js";
import { avisar } from "../avisos.js";
import { definirGuardaDeSaida } from "../rotas.js";
import { esquecerCachesDoFormulario } from "../transacao-form.js";

const SUGESTOES_RAPIDAS = {
  despesa: ["Supermercado/Feira", "Restaurantes e Lanchonetes", "Delivery", "Aplicativos de Corridas", "Farmácia e Medicamentos", "Combustível"],
  receita: ["Salário", "Freelance e Trabalhos Extras", "Reembolsos", "Vendas", "Presentes Recebidos", "Outras Receitas"],
};
const ETAPAS = ["Arquivo", "Conferir", "Pronto"];
const RENDIMENTO_PEQUENO = 5;
const CATEGORIA_RENDIMENTOS = "Rendimentos de Investimentos";
const dataExtenso = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long" });
const partesDia = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short" });
const diaMes = (iso) => {
  const partes = partesDia.formatToParts(new Date(iso));
  const dia = partes.find((p) => p.type === "day")?.value ?? "";
  const mes = (partes.find((p) => p.type === "month")?.value ?? "").replace(".", "");
  return `${dia} ${mes}`;
};

function etapas(atual, concluido = false) {
  return el(
    "ol",
    { class: "im-etapas", "aria-label": "Etapas da importação" },
    ETAPAS.map((nome, i) => {
      const feito = i < atual || concluido;
      return el(
        "li",
        { class: `im-etapa${feito ? " feita" : ""}${i === atual ? " atual" : ""}`, "aria-current": i === atual ? "step" : null },
        el("i", { "aria-hidden": "true" }, feito ? icone("sucesso", "ic-sm") : String(i + 1)),
        el("span", { texto: nome }),
        feito ? el("span", { class: "sr", texto: " (concluída)" }) : null,
      );
    }),
  );
}

export async function montar(raiz, { navegar }) {
  const conteudo = el("div", { class: "im-tela" });
  raiz.append(el("h1", { class: "im-titulo-tela", texto: "Importar extrato" }), conteudo);
  let concluida = false;

  function abrirJanela() {
    abrirImportacao({ aoConcluir: () => desenhar() });
  }

  definirGuardaDeSaida(() => {
    if (concluida || !previaGuardada()) return true;
    return confirmar({ titulo: "Sair sem importar?", texto: "A conferência deste extrato vai se perder.", confirmar: "Sair sem importar", cancelar: "Continuar conferindo", perigo: true });
  });

  function telaInicial() {
    const escolher = el("button", { type: "button", class: "btn btn-primario" }, icone("enviar", "ic-sm"), "Escolher arquivo");
    escolher.addEventListener("click", abrirJanela);
    conteudo.replaceChildren(
      etapas(0),
      el(
        "section",
        { class: "im-vazio" },
        el("span", { class: "im-vazio-ic", "aria-hidden": "true" }, icone("enviar")),
        el("h2", { texto: "Traga as transações do seu banco" }),
        el("p", { texto: "Baixe o extrato ou a fatura no app do banco, em OFX ou CSV, e escolha o arquivo aqui." }),
        escolher,
      ),
    );
  }

  async function telaConferir(previa) {
    let categorias = [];
    try {
      categorias = [...(await carregarCategorias()).values()];
    } catch {
      categorias = [];
    }
    if (!raiz.isConnected) return;
    const sugerir = criarSugestor(categorias);
    const porId = new Map(categorias.map((c) => [c.id_categoria, c]));
    const doTipo = (tipo) => categorias.filter((c) => !c.tipo_padrao || c.tipo_padrao === tipo).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

    const itens = previa.itens.map((item, indice) => {
      const sugerida = item.duplicada ? null : sugerir(item.nome, item.tipo);
      const rendimento = !item.duplicada && item.tipo === "receita" && sugerida?.nome === CATEGORIA_RENDIMENTOS && Number(item.valor) < RENDIMENTO_PEQUENO;
      return { ...item, indice, id_categoria: sugerida?.id_categoria ?? null, pendente: !item.duplicada && !sugerida, rendimento, incluir: !item.duplicada && !rendimento };
    });
    const novos = itens.filter((i) => !i.duplicada);
    const pendentes = novos.filter((i) => i.pendente);
    const prontos = novos.filter((i) => !i.pendente && !i.rendimento);
    const rendimentos = novos.filter((i) => i.rendimento);
    const repetidos = itens.filter((i) => i.duplicada);

    const resumo = el("dl", { class: "im-resumo" });
    const importar = el("button", { type: "button", class: "btn btn-primario" });
    const cancelar = el("button", { type: "button", class: "btn btn-secundario", texto: "Cancelar" });
    const aviso = el("div", { class: "mensagem", role: "alert" });
    const contagemPendentes = el("span", { class: "im-contagem" });

    function selecionados() {
      return novos.filter((i) => i.incluir);
    }

    function atualizarTotais() {
      const lista = selecionados();
      const soma = (tipo) => lista.filter((i) => i.tipo === tipo).reduce((total, i) => total + Number(i.valor), 0);
      resumo.replaceChildren(
        el("div", {}, el("dt", { texto: "Novas" }), el("dd", { texto: String(lista.length) })),
        el("div", {}, el("dt", { texto: "Gastos" }), el("dd", { class: "despesa", texto: moedaComSinal(soma("despesa"), "despesa") })),
        el("div", {}, el("dt", { texto: "Ganhos" }), el("dd", { class: "receita", texto: moedaComSinal(soma("receita"), "receita") })),
      );
      importar.textContent = lista.length === 1 ? "Importar 1 transação" : `Importar ${lista.length} transações`;
      importar.disabled = lista.length === 0;
      const faltam = pendentes.filter((i) => i.incluir && !i.id_categoria).length;
      contagemPendentes.textContent = String(faltam);
    }

    function caixaIncluir(item) {
      const caixa = el("input", { type: "checkbox", class: "im-incluir", "aria-label": `Importar ${item.nome}` });
      caixa.checked = item.incluir;
      caixa.addEventListener("change", () => {
        item.incluir = caixa.checked;
        caixa.closest(".im-linha")?.classList.toggle("fora", !item.incluir);
        atualizarTotais();
      });
      return caixa;
    }

    function seletorCategoria(item, aoMudar) {
      const select = el("select", { class: "im-cat-select", "aria-label": `Categoria de ${item.nome}` });
      const atual = porId.get(item.id_categoria);
      select.append(el("option", { value: item.id_categoria ?? "", texto: atual?.nome ?? "Sem categoria" }));
      let preenchido = false;
      const preencher = () => {
        if (preenchido) return;
        preenchido = true;
        const valor = select.value;
        select.replaceChildren(el("option", { value: "", texto: "Sem categoria" }), ...doTipo(item.tipo).map((c) => el("option", { value: c.id_categoria, texto: c.nome })));
        select.value = valor;
      };
      for (const evento of ["pointerdown", "focus", "keydown"]) select.addEventListener(evento, preencher);
      select.addEventListener("change", () => {
        item.id_categoria = select.value || null;
        aoMudar?.();
      });
      return select;
    }

    function campoCategoria(item) {
      const lugar = el("span", { class: "im-cat" });
      const desenharCampo = () => {
        lugar.style.setProperty("--cor", corDaCategoria(porId.get(item.id_categoria)));
        lugar.replaceChildren(el("i", { "aria-hidden": "true" }), seletorCategoria(item, desenharCampo));
      };
      desenharCampo();
      return lugar;
    }

    function linhaBase(item, extra = []) {
      return el(
        "li",
        { class: `im-linha im-${item.tipo}${item.incluir ? "" : " fora"}` },
        item.duplicada ? el("span", { class: "im-incluir-vazio", "aria-hidden": "true" }) : caixaIncluir(item),
        el("span", { class: "im-data", texto: diaMes(item.data_hora) }),
        el("span", { class: "im-nome", texto: item.nome, title: item.nome }),
        el("span", { class: `im-valor ${item.tipo}`, texto: moedaComSinal(item.valor, item.tipo) }),
        ...extra,
      );
    }

    function linhaPendente(item) {
      const chips = el("div", { class: "im-chips", role: "group", "aria-label": `Categoria de ${item.nome}` });
      const rapidas = SUGESTOES_RAPIDAS[item.tipo]
        .map((nome) => categorias.find((c) => c.nome === nome))
        .filter(Boolean)
        .slice(0, 3);
      const desenharChips = () => {
        chips.replaceChildren();
        const escolhida = porId.get(item.id_categoria);
        const lista = escolhida && !rapidas.includes(escolhida) ? [...rapidas, escolhida] : rapidas;
        for (const cat of lista) {
          const chip = el("button", { type: "button", class: "im-chip", "aria-pressed": String(item.id_categoria === cat.id_categoria) }, el("i", { "aria-hidden": "true" }), cat.nome);
          chip.style.setProperty("--cor", corDaCategoria(cat));
          chip.addEventListener("click", () => {
            item.id_categoria = item.id_categoria === cat.id_categoria ? null : cat.id_categoria;
            desenharChips();
            atualizarTotais();
            chips.querySelector(`[aria-pressed="true"]`)?.focus();
          });
          chips.append(chip);
        }
        const outra = seletorCategoria({ ...item, id_categoria: null }, () => {});
        outra.classList.add("im-chip", "im-chip-outra");
        outra.firstChild.textContent = "Outra…";
        outra.addEventListener("change", () => {
          item.id_categoria = outra.value || null;
          desenharChips();
          atualizarTotais();
        });
        chips.append(outra);
      };
      desenharChips();
      return linhaBase(item, [chips]);
    }

    const blocos = [];
    const datas = itens.map((i) => i.data_hora).sort();
    const primeiro = datas[0];
    const ultimo = datas.at(-1);
    const periodo = primeiro && ultimo ? `${itens.length} ${itens.length === 1 ? "lançamento" : "lançamentos"} de ${dataExtenso.format(new Date(primeiro))} a ${dataExtenso.format(new Date(ultimo))}` : "";
    const trocar = el("button", { type: "button", class: "btn btn-texto", texto: "Trocar" });
    trocar.setAttribute("aria-label", "Trocar arquivo");
    trocar.addEventListener("click", abrirJanela);
    blocos.push(
      etapas(1),
      el(
        "div",
        { class: "im-arquivo" },
        el("span", { class: "im-doc", "aria-hidden": "true", texto: previa.formato.toUpperCase() }),
        el("span", { class: "im-arquivo-texto" }, el("b", { texto: previa.arquivo }), el("small", { texto: periodo })),
        trocar,
      ),
      resumo,
    );

    const considerados = novos.filter((i) => !i.rendimento);
    const receitas = considerados.filter((i) => i.tipo === "receita").length;
    const pareceFatura = considerados.length >= 4 && receitas / considerados.length >= 0.75;
    function botaoInverter(texto) {
      const botao = el("button", { type: "button", class: "btn btn-secundario", texto });
      botao.addEventListener("click", async () => {
        ocupado(botao, true, "Relendo…");
        try {
          const nova = await pedirPrevia({ base64: previa.base64, inverter: !previa.inverter, mapeamento: previa.mapeamento });
          Object.assign(previa, nova, { inverter: !previa.inverter });
          desenhar();
        } catch (erro) {
          if (!(erro instanceof ErroApi)) throw erro;
          ocupado(botao, false);
          avisar(erro.message, { tipo: "erro" });
        }
      });
      return botao;
    }
    if (pareceFatura) {
      blocos.push(el("div", { class: "im-dica" }, icone("alerta", "ic-sm"), el("span", { texto: "Quase tudo veio como ganho. Parece uma fatura de cartão?" }), botaoInverter("Inverter gastos e ganhos")));
    } else if (previa.inverter) {
      blocos.push(el("div", { class: "im-dica im-dica-suave" }, icone("info", "ic-sm"), el("span", { texto: "Lido como fatura de cartão: gastos e ganhos invertidos." }), botaoInverter("Desfazer")));
    }

    if (pendentes.length) {
      blocos.push(
        el(
          "section",
          { class: "im-grupo atencao", "aria-labelledby": "im-titulo-pendentes" },
          el("h2", { id: "im-titulo-pendentes" }, icone("alerta", "ic-sm"), "Escolha a categoria", contagemPendentes, el("span", { class: "im-grupo-dica", texto: "Ou importe sem categoria" })),
          el("ul", { class: "im-lista" }, pendentes.map(linhaPendente)),
        ),
      );
    }
    if (prontos.length) {
      blocos.push(
        el(
          "details",
          { class: "im-grupo", open: true },
          el("summary", {}, "Prontas para importar", el("span", { class: "im-contagem", texto: String(prontos.length) }), el("span", { class: "im-grupo-dica", texto: "Categoria sugerida pelo nome" })),
          el("ul", { class: "im-lista" }, prontos.map((item) => linhaBase(item, [campoCategoria(item)]))),
        ),
      );
    }
    if (rendimentos.length) {
      const total = rendimentos.reduce((soma, i) => soma + Number(i.valor), 0);
      blocos.push(
        el(
          "details",
          { class: "im-grupo" },
          el("summary", {}, "Rendimentos pequenos", el("span", { class: "im-contagem", texto: String(rendimentos.length) }), el("span", { class: "im-grupo-dica", texto: `${moedaComSinal(total, "receita")} fora da importação` })),
          el("ul", { class: "im-lista" }, rendimentos.map((item) => linhaBase(item, [campoCategoria(item)]))),
        ),
      );
    }
    if (repetidos.length) {
      blocos.push(
        el(
          "details",
          { class: "im-grupo" },
          el("summary", {}, "Já estavam no Finanças", el("span", { class: "im-contagem", texto: String(repetidos.length) }), el("span", { class: "im-grupo-dica", texto: "Não serão importadas de novo" })),
          el("ul", { class: "im-lista im-repetidas" }, repetidos.map((item) => linhaBase(item))),
        ),
      );
    }
    if (!novos.length) {
      blocos.push(el("p", { class: "im-nota", texto: "Todas as transações deste arquivo já estão no Finanças. Não há nada novo para importar." }));
    }
    blocos.push(el("div", { class: "im-rodape" }, aviso, el("div", { class: "im-rodape-botoes" }, cancelar, importar)));
    conteudo.replaceChildren(...blocos);
    atualizarTotais();

    cancelar.addEventListener("click", async () => {
      const sim = await confirmar({ titulo: "Cancelar a importação?", texto: "Nada deste arquivo será importado.", confirmar: "Cancelar importação", cancelar: "Continuar conferindo", perigo: true });
      if (!sim) return;
      esquecerPrevia();
      desenhar();
    });

    importar.addEventListener("click", async () => {
      mensagem(aviso, "erro", "");
      const lista = selecionados();
      if (!lista.length) return;
      ocupado(importar, true, "Importando…");
      try {
        const resultado = await api.post("/importacoes", {
          itens: lista.map((i) => ({ data_hora: i.data_hora, valor: i.valor, tipo: i.tipo, nome: i.nome, id_categoria: i.id_categoria, id_externo: i.id_externo })),
        });
        esquecerCachesDoFormulario();
        concluida = true;
        const maisRecente = lista.reduce((a, b) => (a.data_hora > b.data_hora ? a : b)).data_hora;
        esquecerPrevia();
        telaPronto(resultado, maisRecente);
      } catch (erro) {
        if (!(erro instanceof ErroApi)) throw erro;
        ocupado(importar, false);
        mensagem(aviso, "erro", erro.message);
      }
    });
  }

  function telaPronto(resultado, dataReferencia) {
    const mes = dataReferencia.slice(0, 7);
    const ver = el("a", { class: "btn btn-primario", href: `#/transacoes?mes=${mes}` }, "Ver transações");
    const outro = el("button", { type: "button", class: "btn btn-secundario", texto: "Importar outro extrato" });
    outro.addEventListener("click", () => {
      concluida = false;
      telaInicial();
      abrirJanela();
    });
    const titulo = resultado.criadas === 1 ? "1 transação importada" : `${resultado.criadas} transações importadas`;
    conteudo.replaceChildren(
      etapas(2, true),
      el(
        "section",
        { class: "im-vazio im-pronto", "aria-live": "polite" },
        el("span", { class: "im-vazio-ic", "aria-hidden": "true" }, icone("sucesso")),
        el("h2", { texto: titulo }),
        resultado.ignoradas ? el("p", { texto: `${resultado.ignoradas} já estavam no Finanças e ficaram de fora.` }) : null,
        el("div", { class: "im-pronto-botoes" }, ver, outro),
      ),
    );
    ver.focus();
  }

  function desenhar() {
    const previa = previaGuardada();
    if (previa) telaConferir(previa);
    else telaInicial();
  }

  desenhar();
  if (!previaGuardada()) abrirJanela();
}
