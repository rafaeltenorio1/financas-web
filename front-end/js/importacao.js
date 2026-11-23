import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";

const TAMANHO_MAXIMO = 2 * 1024 * 1024;
const CAMPOS_MAPEAMENTO = [
  ["data", "Data", true],
  ["valor", "Valor", true],
  ["descricao", "Descrição", true],
  ["identificador", "Identificador (opcional)", false],
];

let previaAtual = null;

export function previaGuardada() {
  return previaAtual;
}

export function esquecerPrevia() {
  previaAtual = null;
}

function lerComoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.addEventListener("load", () => resolver(leitor.result));
    leitor.addEventListener("error", () => rejeitar(leitor.error));
    leitor.readAsDataURL(arquivo);
  });
}

export async function pedirPrevia({ base64, inverter, mapeamento = null }) {
  const corpo = { arquivo_base64: base64, inverter_sinal: inverter };
  if (mapeamento) corpo.mapeamento = mapeamento;
  return api.post("/importacoes/previa", corpo);
}

function tamanhoLegivel(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
}

export function abrirImportacao({ aoConcluir } = {}) {
  const origemDoFoco = document.activeElement;
  const estado = { arquivo: null, base64: null, colunas: null };

  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
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
  const aviso = el("div", { class: "mensagem", role: "alert" });
  const continuar = el("button", { type: "submit", class: "btn btn-primario", disabled: true, texto: "Continuar" });

  const formulario = el(
    "form",
    { class: "im-form", novalidate: true },
    el("div", { class: "im-topo" }, el("h2", { id: "im-titulo", texto: "Importar extrato" }), fechar),
    entrada,
    zona,
    escolhido,
    blocoFatura,
    mapa,
    aviso,
    el("div", { class: "im-botoes" }, continuar),
  );
  const dialogo = el("dialog", { class: "im-janela", "aria-labelledby": "im-titulo" }, formulario);

  function mostrarArquivo() {
    escolhido.hidden = !estado.arquivo;
    zona.classList.toggle("com-arquivo", Boolean(estado.arquivo));
    continuar.disabled = !estado.arquivo;
    if (!estado.arquivo) return;
    const extensao = (estado.arquivo.name.split(".").pop() || "").slice(0, 4).toUpperCase();
    const trocar = el("button", { type: "button", class: "btn btn-texto", texto: "Trocar" });
    trocar.addEventListener("click", () => entrada.click());
    escolhido.replaceChildren(
      el("span", { class: "im-doc", "aria-hidden": "true", texto: extensao }),
      el("span", { class: "im-escolhido-texto" }, el("b", { texto: estado.arquivo.name }), el("small", { texto: tamanhoLegivel(estado.arquivo.size) })),
      trocar,
    );
  }

  async function usarArquivo(arquivo) {
    mensagem(aviso, "erro", "");
    estado.colunas = null;
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
    continuar.focus();
  }

  function mostrarMapa(colunas) {
    estado.colunas = colunas;
    for (const [chave, , obrigatorio] of CAMPOS_MAPEAMENTO) {
      const select = selects[chave];
      select.replaceChildren(el("option", { value: "", texto: obrigatorio ? "Escolha a coluna" : "Nenhuma" }), ...colunas.map((c) => el("option", { value: c, texto: c })));
    }
    mapa.hidden = false;
    selects.data.focus();
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

  fechar.addEventListener("click", () => dialogo.close());
  dialogo.addEventListener("click", (evento) => {
    if (evento.target === dialogo) dialogo.close();
  });
  dialogo.addEventListener("close", () => {
    dialogo.remove();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(aviso, "erro", "");
    if (!estado.base64) return;
    let mapeamento = null;
    if (estado.colunas) {
      const faltando = CAMPOS_MAPEAMENTO.find(([chave, , obrigatorio]) => obrigatorio && !selects[chave].value);
      if (faltando) {
        mensagem(aviso, "erro", `Escolha a coluna de ${faltando[1].toLowerCase()}.`);
        return selects[faltando[0]].focus();
      }
      mapeamento = Object.fromEntries(CAMPOS_MAPEAMENTO.map(([chave]) => [chave, selects[chave].value || null]));
    }
    ocupado(continuar, true, "Lendo o arquivo…");
    try {
      const resposta = await pedirPrevia({ base64: estado.base64, inverter: fatura.checked, mapeamento });
      previaAtual = { ...resposta, arquivo: estado.arquivo.name, base64: estado.base64, inverter: fatura.checked, mapeamento };
      dialogo.close();
      aoConcluir?.(previaAtual);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      const colunas = erro.detalhe?.colunas;
      if (erro.status === 422 && Array.isArray(colunas) && colunas.length && !estado.colunas) {
        mostrarMapa(colunas);
        mensagem(aviso, "info", "Não reconhecemos as colunas deste CSV. Indique quais são.");
      } else {
        mensagem(aviso, "erro", erro.message);
      }
    } finally {
      if (dialogo.isConnected) ocupado(continuar, false);
    }
  });

  document.body.append(dialogo);
  dialogo.showModal();
  entrada.focus();
  return dialogo;
}
