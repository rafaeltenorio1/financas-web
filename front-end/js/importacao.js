import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { carregarCategorias } from "./categorias.js";
import { confirmar } from "./confirmar.js";
import { avisar } from "./avisos.js";
import { esquecerCachesDoFormulario } from "./transacao-form.js";
import { montarConferir } from "./importacao-conferir.js";

const TAMANHO_MAXIMO = 2 * 1024 * 1024;
const ETAPAS = ["Arquivo", "Conferir", "Pronto"];
const CAMPOS_MAPEAMENTO = [
  ["data", "Data", true],
  ["valor", "Valor", true],
  ["descricao", "Descrição", true],
  ["identificador", "Identificador (opcional)", false],
];

function lerComoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.addEventListener("load", () => resolver(leitor.result));
    leitor.addEventListener("error", () => rejeitar(leitor.error));
    leitor.readAsDataURL(arquivo);
  });
}

function tamanhoLegivel(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

export function abrirImportacao({ aoImportar } = {}) {
  const origemDoFoco = document.activeElement;
  const estado = { etapa: 0, arquivo: null, base64: null, colunas: null, mapeamento: null, previa: null, conferir: null, resultado: null, mesImportado: null };

  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
  const listaEtapas = el("ol", { class: "im-etapas", "aria-label": "Etapas da importação" });
  const corpo = el("div", { class: "im-corpo" });
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const botoes = el("div", { class: "im-botoes" });
  const dialogo = el(
    "dialog",
    { class: "im-janela", "aria-labelledby": "im-titulo" },
    el("header", { class: "im-cabecalho" }, el("div", { class: "im-topo" }, el("h2", { id: "im-titulo", texto: "Importar extrato" }), fechar), listaEtapas),
    corpo,
    el("footer", { class: "im-rodape" }, aviso, botoes),
  );

  const entrada = el("input", { type: "file", id: "im-arquivo", name: "arquivo", accept: ".ofx,.csv,.txt,text/csv,application/x-ofx", class: "im-entrada" });
  const zona = el(
    "label",
    { class: "im-zona", for: "im-arquivo" },
    el("span", { class: "im-zona-ic", "aria-hidden": "true" }, icone("enviar")),
    el("strong", { texto: "Arraste o extrato aqui" }),
    el("span", { class: "im-zona-ou" }, "ou ", el("span", { class: "im-zona-link", texto: "escolha no computador" })),
    el("small", { texto: "OFX ou CSV, até 2 MB" }),
  );
  const escolhido = el("div", { class: "im-escolhido", hidden: true });
  const fatura = el("input", { type: "checkbox", role: "switch", id: "im-fatura", name: "fatura", "aria-describedby": "im-fatura-ajuda" });
  const blocoFatura = el(
    "label",
    { class: "im-opcao", for: "im-fatura" },
    el("span", {}, el("strong", { texto: "É fatura de cartão de crédito" }), el("small", { id: "im-fatura-ajuda", texto: "Nela as compras vêm com sinal trocado." })),
    fatura,
    el("span", { class: "interruptor", "aria-hidden": "true" }),
  );
  const mapa = el("fieldset", { class: "im-mapa", hidden: true }, el("legend", { texto: "Quais colunas são essas?" }));
  const selects = {};
  for (const [chave, rotulo, obrigatorio] of CAMPOS_MAPEAMENTO) {
    const select = el("select", { class: "entrada", id: `im-col-${chave}`, name: chave, required: obrigatorio });
    selects[chave] = select;
    mapa.append(el("label", { for: `im-col-${chave}` }, el("span", { texto: rotulo }), select));
  }
  const etapaArquivo = el("div", { class: "im-etapa-arquivo" }, entrada, zona, escolhido, blocoFatura, mapa);

  function desenharEtapas() {
    listaEtapas.replaceChildren(
      ...ETAPAS.map((nome, i) => {
        const feito = i < estado.etapa || estado.etapa === 2;
        const atual = i === estado.etapa;
        return el(
          "li",
          { class: `im-etapa${feito ? " feita" : ""}${atual ? " atual" : ""}`, "aria-current": atual ? "step" : null },
          el("i", { "aria-hidden": "true" }, feito ? icone("sucesso", "ic-sm") : String(i + 1)),
          el("span", { texto: nome }),
        );
      }),
    );
  }

  function botao(texto, classe, aoClicar) {
    const b = el("button", { type: "button", class: `btn ${classe}`, texto });
    b.addEventListener("click", aoClicar);
    return b;
  }

  function irPara(etapa) {
    estado.etapa = etapa;
    dialogo.dataset.etapa = ["arquivo", "conferir", "pronto"][etapa];
    mensagem(aviso, "erro", "");
    desenharEtapas();
    corpo.scrollTop = 0;
    if (etapa === 0) mostrarArquivo();
    else if (etapa === 1) mostrarConferir();
    else mostrarPronto();
  }

  function mostrarEscolhido() {
    escolhido.hidden = !estado.arquivo;
    zona.classList.toggle("com-arquivo", Boolean(estado.arquivo));
    if (!estado.arquivo) return;
    const extensao = (estado.arquivo.name.split(".").pop() || "").slice(0, 4).toUpperCase();
    const trocar = botao("Trocar", "btn-texto", () => entrada.click());
    trocar.setAttribute("aria-label", "Trocar arquivo");
    escolhido.replaceChildren(
      el("span", { class: "im-doc", "aria-hidden": "true", texto: extensao }),
      el("span", { class: "im-escolhido-texto" }, el("b", { texto: estado.arquivo.name }), el("small", { texto: tamanhoLegivel(estado.arquivo.size) })),
      trocar,
    );
  }

  function mostrarArquivo() {
    corpo.replaceChildren(etapaArquivo);
    mostrarEscolhido();
    const continuar = el("button", { type: "button", class: "btn btn-primario", disabled: !estado.arquivo, texto: "Continuar" });
    continuar.addEventListener("click", () => lerArquivo(continuar));
    botoes.replaceChildren(botao("Cancelar", "btn-secundario", () => pedirFechamento().then((ok) => ok && dialogo.close())), continuar);
    entrada.focus();
  }

  async function usarArquivo(arquivo) {
    mensagem(aviso, "erro", "");
    estado.colunas = null;
    estado.mapeamento = null;
    mapa.hidden = true;
    if (!arquivo) return;
    if (arquivo.size > TAMANHO_MAXIMO) {
      estado.arquivo = null;
      mostrarArquivo();
      mensagem(aviso, "erro", "O arquivo passa de 2 MB. Exporte um período menor no app do banco.");
      return;
    }
    estado.arquivo = arquivo;
    estado.base64 = await lerComoBase64(arquivo);
    mostrarArquivo();
    botoes.querySelector(".btn-primario")?.focus();
  }

  function mostrarMapa(colunas) {
    estado.colunas = colunas;
    for (const [chave, , obrigatorio] of CAMPOS_MAPEAMENTO) {
      selects[chave].replaceChildren(el("option", { value: "", texto: obrigatorio ? "Escolha a coluna" : "Nenhuma" }), ...colunas.map((c) => el("option", { value: c, texto: c })));
    }
    mapa.hidden = false;
    selects.data.focus();
  }

  async function pedirPrevia(inverter) {
    const corpoPedido = { arquivo_base64: estado.base64, inverter_sinal: inverter };
    if (estado.mapeamento) corpoPedido.mapeamento = estado.mapeamento;
    const resposta = await api.post("/importacoes/previa", corpoPedido);
    return { ...resposta, inverter };
  }

  async function lerArquivo(continuar) {
    mensagem(aviso, "erro", "");
    if (!estado.base64) return;
    if (estado.colunas) {
      const faltando = CAMPOS_MAPEAMENTO.find(([chave, , obrigatorio]) => obrigatorio && !selects[chave].value);
      if (faltando) {
        mensagem(aviso, "erro", `Escolha a coluna de ${faltando[1].toLowerCase()}.`);
        return selects[faltando[0]].focus();
      }
      estado.mapeamento = Object.fromEntries(CAMPOS_MAPEAMENTO.map(([chave]) => [chave, selects[chave].value || null]));
    }
    ocupado(continuar, true, "Lendo o arquivo…");
    try {
      estado.previa = await pedirPrevia(fatura.checked);
      irPara(1);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (continuar.isConnected) ocupado(continuar, false);
      const colunas = erro.detalhe?.colunas;
      if (erro.status === 422 && Array.isArray(colunas) && colunas.length && !estado.colunas) {
        mostrarMapa(colunas);
        mensagem(aviso, "info", "Não reconhecemos as colunas deste CSV. Indique quais são.");
      } else {
        mensagem(aviso, "erro", erro.message);
      }
    }
  }

  async function mostrarConferir() {
    corpo.replaceChildren(el("p", { class: "im-carregando", texto: "Preparando a conferência…" }));
    botoes.replaceChildren();
    let categorias = [];
    try {
      categorias = [...(await carregarCategorias()).values()];
    } catch {
      categorias = [];
    }
    if (!dialogo.open || estado.etapa !== 1) return;
    const importar = el("button", { type: "button", class: "btn btn-primario" });
    estado.conferir = montarConferir({
      previa: estado.previa,
      nomeArquivo: estado.arquivo.name,
      categorias,
      aoTrocar: () => irPara(0),
      aoInverter: async () => {
        try {
          estado.previa = await pedirPrevia(!estado.previa.inverter);
          fatura.checked = estado.previa.inverter;
          mostrarConferir();
          return true;
        } catch (erro) {
          if (!(erro instanceof ErroApi)) throw erro;
          avisar(erro.message, { tipo: "erro" });
          return false;
        }
      },
      aoMudar: (quantidade) => {
        importar.textContent = quantidade === 1 ? "Importar 1 transação" : `Importar ${quantidade} transações`;
        importar.disabled = quantidade === 0;
      },
    });
    importar.addEventListener("click", () => importarSelecionadas(importar));
    corpo.replaceChildren(estado.conferir.elemento);
    botoes.replaceChildren(botao("Voltar", "btn-secundario", () => irPara(0)), importar);
    importar.focus();
  }

  async function importarSelecionadas(importar) {
    mensagem(aviso, "erro", "");
    const itens = estado.conferir.paraEnviar();
    if (!itens.length) return;
    ocupado(importar, true, "Importando…");
    try {
      estado.resultado = await api.post("/importacoes", { itens });
      estado.mesImportado = itens.reduce((a, b) => (a.data_hora > b.data_hora ? a : b)).data_hora.slice(0, 7);
      esquecerCachesDoFormulario();
      irPara(2);
      aoImportar?.(estado.resultado);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (importar.isConnected) ocupado(importar, false);
      mensagem(aviso, "erro", erro.message);
    }
  }

  function mostrarPronto() {
    const { criadas, ignoradas } = estado.resultado;
    corpo.replaceChildren(
      el(
        "section",
        { class: "im-pronto", "aria-live": "polite" },
        el("span", { class: "im-pronto-ic", "aria-hidden": "true" }, icone("sucesso")),
        el("h3", { texto: criadas === 1 ? "1 transação importada" : `${criadas} transações importadas` }),
        ignoradas ? el("p", { texto: `${ignoradas} já estavam no Finanças e ficaram de fora.` }) : null,
      ),
    );
    const ver = el("a", { class: "btn btn-primario", href: `#/transacoes?mes=${estado.mesImportado}`, texto: "Ver transações" });
    ver.addEventListener("click", () => dialogo.close());
    const outro = botao("Importar outro extrato", "btn-secundario", () => {
      Object.assign(estado, { arquivo: null, base64: null, colunas: null, mapeamento: null, previa: null, conferir: null, resultado: null });
      entrada.value = "";
      fatura.checked = false;
      mapa.hidden = true;
      irPara(0);
    });
    botoes.replaceChildren(outro, ver);
    ver.focus();
  }

  async function pedirFechamento() {
    if (estado.etapa !== 1) return true;
    return confirmar({ titulo: "Sair sem importar?", texto: "A conferência deste extrato vai se perder.", confirmar: "Sair sem importar", cancelar: "Continuar conferindo", perigo: true });
  }

  entrada.addEventListener("change", () => usarArquivo(entrada.files[0]));
  for (const evento of ["dragenter", "dragover"]) {
    zona.addEventListener(evento, (e) => {
      e.preventDefault();
      zona.classList.add("arrastando");
    });
  }
  for (const evento of ["dragleave", "drop"]) zona.addEventListener(evento, () => zona.classList.remove("arrastando"));
  zona.addEventListener("drop", (e) => {
    e.preventDefault();
    usarArquivo(e.dataTransfer.files[0]);
  });

  fechar.addEventListener("click", async () => {
    if (await pedirFechamento()) dialogo.close();
  });
  dialogo.addEventListener("cancel", async (evento) => {
    evento.preventDefault();
    if (await pedirFechamento()) dialogo.close();
  });
  dialogo.addEventListener("close", () => {
    dialogo.remove();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
  });

  document.body.append(dialogo);
  dialogo.showModal();
  irPara(0);
  return dialogo;
}
