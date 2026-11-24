import { el, icone, ocupado } from "./dom.js";
import { corDaCategoria } from "./categorias.js";
import { criarSugestor } from "./sugestao-categoria.js";
import { moedaComSinal } from "./formatos.js";

const SUGESTOES_RAPIDAS = {
  despesa: ["Supermercado/Feira", "Restaurantes e Lanchonetes", "Delivery", "Aplicativos de Corridas", "Farmácia e Medicamentos", "Combustível"],
  receita: ["Salário", "Freelance e Trabalhos Extras", "Reembolsos", "Vendas", "Presentes Recebidos", "Outras Receitas"],
};
const RENDIMENTO_PEQUENO = 5;
const CATEGORIA_RENDIMENTOS = "Rendimentos de Investimentos";
const dataExtenso = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "long" });
const partesDia = new Intl.DateTimeFormat("pt-BR", { day: "numeric", month: "short" });

function diaMes(iso) {
  const partes = partesDia.formatToParts(new Date(iso));
  const dia = partes.find((p) => p.type === "day")?.value ?? "";
  const mes = (partes.find((p) => p.type === "month")?.value ?? "").replace(".", "");
  return `${dia} ${mes}`;
}

export function montarConferir({ previa, nomeArquivo, categorias, aoTrocar, aoInverter, aoMudar }) {
  const sugerir = criarSugestor(categorias);
  const porId = new Map(categorias.map((c) => [c.id_categoria, c]));
  const doTipo = (tipo) => categorias.filter((c) => !c.tipo_padrao || c.tipo_padrao === tipo).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));

  const itens = previa.itens.map((item) => {
    const sugerida = item.duplicada ? null : sugerir(item.nome, item.tipo);
    const rendimento = !item.duplicada && item.tipo === "receita" && sugerida?.nome === CATEGORIA_RENDIMENTOS && Number(item.valor) < RENDIMENTO_PEQUENO;
    return { ...item, id_categoria: sugerida?.id_categoria ?? null, pendente: !item.duplicada && !sugerida, rendimento, incluir: !item.duplicada && !rendimento };
  });
  const novos = itens.filter((i) => !i.duplicada);
  const pendentes = novos.filter((i) => i.pendente);
  const prontos = novos.filter((i) => !i.pendente && !i.rendimento);
  const rendimentos = novos.filter((i) => i.rendimento);
  const repetidos = itens.filter((i) => i.duplicada);

  const resumo = el("dl", { class: "im-resumo" });
  const contagemPendentes = el("span", { class: "im-contagem" });
  const selecionados = () => novos.filter((i) => i.incluir);

  function atualizarTotais() {
    const lista = selecionados();
    const soma = (tipo) => lista.filter((i) => i.tipo === tipo).reduce((total, i) => total + Number(i.valor), 0);
    resumo.replaceChildren(
      el("div", {}, el("dt", { texto: "Novas" }), el("dd", { texto: String(lista.length) })),
      el("div", {}, el("dt", { texto: "Gastos" }), el("dd", { class: "despesa", texto: moedaComSinal(soma("despesa"), "despesa") })),
      el("div", {}, el("dt", { texto: "Ganhos" }), el("dd", { class: "receita", texto: moedaComSinal(soma("receita"), "receita") })),
    );
    contagemPendentes.textContent = String(pendentes.filter((i) => i.incluir && !i.id_categoria).length);
    aoMudar?.(lista.length);
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

  function seletorCategoria(item, rotuloVazio = "Sem categoria") {
    const select = el("select", { class: "im-cat-select", "aria-label": `Categoria de ${item.nome}` });
    const atual = porId.get(item.id_categoria);
    select.append(el("option", { value: item.id_categoria ?? "", texto: atual?.nome ?? rotuloVazio }));
    let preenchido = false;
    const preencher = () => {
      if (preenchido) return;
      preenchido = true;
      const valor = select.value;
      select.replaceChildren(el("option", { value: "", texto: rotuloVazio }), ...doTipo(item.tipo).map((c) => el("option", { value: c.id_categoria, texto: c.nome })));
      select.value = valor;
    };
    for (const evento of ["pointerdown", "focus", "keydown"]) select.addEventListener(evento, preencher);
    return select;
  }

  function campoCategoria(item) {
    const lugar = el("span", { class: "im-cat" });
    const desenhar = () => {
      lugar.style.setProperty("--cor", corDaCategoria(porId.get(item.id_categoria)));
      const select = seletorCategoria(item);
      select.addEventListener("change", () => {
        item.id_categoria = select.value || null;
        desenhar();
        lugar.querySelector("select")?.focus();
      });
      lugar.replaceChildren(el("i", { "aria-hidden": "true" }), select);
    };
    desenhar();
    return lugar;
  }

  function linha(item, extra = []) {
    return el(
      "li",
      { class: `im-linha${item.incluir ? "" : " fora"}` },
      item.duplicada ? el("span", { "aria-hidden": "true" }) : caixaIncluir(item),
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
    const desenhar = () => {
      chips.replaceChildren();
      const escolhida = porId.get(item.id_categoria);
      const lista = escolhida && !rapidas.includes(escolhida) ? [...rapidas, escolhida] : rapidas;
      for (const cat of lista) {
        const chip = el("button", { type: "button", class: "im-chip", "aria-pressed": String(item.id_categoria === cat.id_categoria) }, el("i", { "aria-hidden": "true" }), cat.nome);
        chip.style.setProperty("--cor", corDaCategoria(cat));
        chip.addEventListener("click", () => {
          item.id_categoria = item.id_categoria === cat.id_categoria ? null : cat.id_categoria;
          desenhar();
          atualizarTotais();
          chips.querySelector('[aria-pressed="true"]')?.focus();
        });
        chips.append(chip);
      }
      const outra = seletorCategoria({ ...item, id_categoria: null }, "Outra…");
      outra.classList.add("im-chip", "im-chip-outra");
      outra.addEventListener("change", () => {
        item.id_categoria = outra.value || null;
        desenhar();
        atualizarTotais();
      });
      chips.append(outra);
    };
    desenhar();
    return linha(item, [chips]);
  }

  function grupo({ titulo, contagem, dica, itensDoGrupo, montarLinha, aberto = true, atencao = false }) {
    const lista = el("ul", { class: "im-lista" }, itensDoGrupo.map(montarLinha));
    if (atencao) {
      return el("section", { class: "im-grupo atencao" }, el("h3", {}, icone("alerta", "ic-sm"), titulo, contagem, el("span", { class: "im-grupo-dica", texto: dica })), lista);
    }
    return el("details", { class: "im-grupo", open: aberto }, el("summary", {}, titulo, contagem, el("span", { class: "im-grupo-dica", texto: dica })), lista);
  }
  const contar = (n) => el("span", { class: "im-contagem", texto: String(n) });

  const datas = itens.map((i) => i.data_hora).sort();
  const periodo = datas.length ? `${itens.length} ${itens.length === 1 ? "lançamento" : "lançamentos"} de ${dataExtenso.format(new Date(datas[0]))} a ${dataExtenso.format(new Date(datas.at(-1)))}` : "";
  const trocar = el("button", { type: "button", class: "btn btn-texto", texto: "Trocar" });
  trocar.setAttribute("aria-label", "Trocar arquivo");
  trocar.addEventListener("click", () => aoTrocar?.());

  const blocos = [
    el(
      "div",
      { class: "im-arquivo" },
      el("span", { class: "im-doc", "aria-hidden": "true", texto: previa.formato.toUpperCase() }),
      el("span", { class: "im-arquivo-texto" }, el("b", { texto: nomeArquivo }), el("small", { texto: periodo })),
      trocar,
    ),
    resumo,
  ];

  const considerados = novos.filter((i) => !i.rendimento);
  const receitas = considerados.filter((i) => i.tipo === "receita").length;
  const pareceFatura = considerados.length >= 4 && receitas / considerados.length >= 0.75;
  const botaoInverter = (texto) => {
    const botao = el("button", { type: "button", class: "btn btn-secundario", texto });
    botao.addEventListener("click", async () => {
      ocupado(botao, true, "Relendo…");
      const deuCerto = await aoInverter?.();
      if (!deuCerto && botao.isConnected) ocupado(botao, false);
    });
    return botao;
  };
  if (pareceFatura) {
    blocos.push(el("div", { class: "im-dica" }, icone("alerta", "ic-sm"), el("span", { texto: "Quase tudo veio como ganho. Parece uma fatura de cartão?" }), botaoInverter("Inverter gastos e ganhos")));
  } else if (previa.inverter) {
    blocos.push(el("div", { class: "im-dica im-dica-suave" }, icone("info", "ic-sm"), el("span", { texto: "Lido como fatura de cartão: gastos e ganhos invertidos." }), botaoInverter("Desfazer")));
  }

  if (pendentes.length) blocos.push(grupo({ titulo: "Escolha a categoria", contagem: contagemPendentes, dica: "Ou importe sem categoria", itensDoGrupo: pendentes, montarLinha: linhaPendente, atencao: true }));
  if (prontos.length) blocos.push(grupo({ titulo: "Prontas para importar", contagem: contar(prontos.length), dica: "Categoria sugerida pelo nome", itensDoGrupo: prontos, montarLinha: (i) => linha(i, [campoCategoria(i)]) }));
  if (rendimentos.length) {
    const total = rendimentos.reduce((soma, i) => soma + Number(i.valor), 0);
    blocos.push(grupo({ titulo: "Rendimentos pequenos", contagem: contar(rendimentos.length), dica: `${moedaComSinal(total, "receita")} fora da importação`, itensDoGrupo: rendimentos, montarLinha: (i) => linha(i, [campoCategoria(i)]), aberto: false }));
  }
  if (repetidos.length) blocos.push(grupo({ titulo: "Já estavam na Balancia", contagem: contar(repetidos.length), dica: "Não serão importadas de novo", itensDoGrupo: repetidos, montarLinha: (i) => linha(i), aberto: false }));
  if (!novos.length) blocos.push(el("p", { class: "im-nota", texto: "Todas as transações deste arquivo já estão na Balancia. Não há nada novo para importar." }));

  const elemento = el("div", { class: "im-conferir" }, ...blocos);
  atualizarTotais();

  return {
    elemento,
    selecionados,
    paraEnviar: () =>
      selecionados().map((i) => ({ data_hora: i.data_hora, valor: i.valor, tipo: i.tipo, nome: i.nome, id_categoria: i.id_categoria, id_externo: i.id_externo })),
  };
}
