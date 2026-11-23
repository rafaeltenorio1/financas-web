import { api, ErroApi } from "./api.js";
import { el, icone, mensagem, ocupado } from "./dom.js";
import { avisar } from "./avisos.js";
import { adivinharIcone, esquecerCategorias, ICONES, iconeValido } from "./categorias.js";
import { esquecerCachesDoFormulario } from "./transacao-form.js";

export const PASTEIS = [
  ["#7dbde8", "Céu"],
  ["#f0a27a", "Pêssego"],
  ["#a996ee", "Lavanda"],
  ["#62c4b8", "Verde-água"],
  ["#ddc170", "Areia"],
  ["#ec93b8", "Rosa"],
];
const TIPOS = [
  ["despesa", "Gastos"],
  ["receita", "Ganhos"],
  [null, "Os dois"],
];
const FUNDO_ESCURO = "#0b2b26";
const CONTRASTE_MINIMO = 3;

function luminancia(hex) {
  const canais = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const [r, g, b] = canais.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contraste(a, b) {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (escuro + 0.05);
}

export function abrirFormularioCategoria({ categoria = null, tipo = "despesa", corSugerida = PASTEIS[0][0], aoSalvar, aoApagar } = {}) {
  const editando = categoria !== null;
  const origemDoFoco = document.activeElement;
  const corInicial = categoria?.cor ?? corSugerida;
  const estado = {
    tipo: editando ? categoria.tipo_padrao : tipo,
    cor: corInicial,
    icone: iconeValido(categoria?.icone) ? categoria.icone : null,
    outraCor: corInicial !== null && !PASTEIS.some(([hex]) => hex === corInicial),
  };

  const fechar = el("button", { type: "button", class: "btn btn-icone", "aria-label": "Fechar" }, icone("fechar"));
  const previaIcone = el("span", { class: "cf-previa-ic", "aria-hidden": "true" });
  const previaNome = el("span", { class: "cf-previa-nome" });
  const previaTipo = el("span", { class: "cf-previa-tipo" });
  const previa = el("div", { class: "cf-previa", "aria-hidden": "true" }, previaIcone, el("span", { class: "cf-previa-texto" }, previaNome, previaTipo));

  const nome = el("input", { class: "entrada", id: "cf-nome", name: "nome", maxlength: 100, autocomplete: "off", placeholder: "Ex.: Pet, Presentes, Moto", "aria-describedby": "cf-nome-erro" });
  nome.value = categoria?.nome ?? "";
  const erroNome = el("p", { class: "campo-erro", id: "cf-nome-erro" });

  const chipsTipo = el("div", { class: "ft-chips", role: "group", "aria-labelledby": "cf-titulo-tipo" });
  const notaTipo = el("p", { class: "campo-ajuda", id: "cf-nota-tipo" });

  const cores = el("div", { class: "cf-cores", role: "group", "aria-labelledby": "cf-titulo-cor" });
  const seletorCor = el("input", { type: "color", id: "cf-outra-cor", name: "outra-cor", value: estado.outraCor ? corInicial : "#5f8a76" });
  const blocoOutraCor = el("label", { class: "cf-outra-cor", for: "cf-outra-cor" }, seletorCor, el("span", { texto: "Escolher a cor" }));
  const avisoCor = el("p", { class: "cf-aviso-cor", "aria-live": "polite" });

  const icones = el("div", { class: "cf-icones", role: "group", "aria-labelledby": "cf-titulo-icone", "aria-describedby": "cf-nota-icone" });
  const notaIcone = el("p", { class: "campo-ajuda", id: "cf-nota-icone" });

  const avisoErro = el("div", { class: "mensagem", role: "alert" });
  const salvar = el("button", { type: "submit", class: "btn btn-primario", texto: editando ? "Salvar alterações" : "Criar categoria" });
  const apagar = editando ? el("button", { type: "button", class: "btn btn-texto cf-apagar" }, icone("erro", "ic-sm"), "Apagar categoria") : null;

  const formulario = el(
    "form",
    { novalidate: true },
    el(
      "div",
      { class: "ft-corpo" },
      el("div", { class: "ft-topo" }, fechar, el("h2", { id: "cf-titulo", texto: editando ? "Editar categoria" : "Nova categoria" })),
      previa,
      el("div", { class: "ft-secao campo" }, el("label", { class: "ft-rotulo", for: "cf-nome", texto: "Nome" }), nome, erroNome),
      el("div", { class: "ft-secao" }, el("h3", { id: "cf-titulo-tipo", texto: "Usar em" }), chipsTipo, notaTipo),
      el("div", { class: "ft-secao" }, el("h3", { id: "cf-titulo-cor", texto: "Cor" }), cores, blocoOutraCor, avisoCor),
      el("div", { class: "ft-secao" }, el("h3", { id: "cf-titulo-icone", texto: "Ícone" }), notaIcone, icones),
      apagar ? el("div", { class: "ft-secao cf-zona-apagar" }, apagar) : null,
    ),
    el("div", { class: "ft-rodape" }, avisoErro, salvar),
  );
  const dialogo = el("dialog", { class: "form-transacao form-categoria", "aria-labelledby": "cf-titulo" }, formulario);

  const iconeEfetivo = () => estado.icone ?? adivinharIcone(nome.value);

  function desenharPrevia() {
    dialogo.style.setProperty("--cor", estado.cor);
    previaIcone.replaceChildren(icone(iconeEfetivo()));
    previaNome.textContent = nome.value.trim() || "Nome da categoria";
    previaNome.classList.toggle("vazio", !nome.value.trim());
    previaTipo.textContent = TIPOS.find(([t]) => t === estado.tipo)[1];
  }

  function desenharTipos() {
    chipsTipo.replaceChildren();
    for (const [chave, rotulo] of TIPOS) {
      const chip = el("button", { type: "button", class: "ft-chip", "aria-pressed": String(estado.tipo === chave), texto: rotulo });
      chip.addEventListener("click", () => {
        estado.tipo = chave;
        desenharTipos();
        desenharPrevia();
        chipsTipo.querySelectorAll("button")[TIPOS.findIndex(([t]) => t === chave)].focus();
      });
      chipsTipo.append(chip);
    }
    notaTipo.textContent = estado.tipo === null ? "Aparece na escolha de categoria de gastos e de ganhos." : "";
  }

  function desenharCores() {
    cores.replaceChildren();
    for (const [hex, rotulo] of PASTEIS) {
      const amostra = el("button", { type: "button", class: "cf-cor", "aria-pressed": String(!estado.outraCor && estado.cor === hex), "aria-label": rotulo, title: rotulo });
      amostra.style.setProperty("--amostra", hex);
      amostra.addEventListener("click", () => {
        estado.cor = hex;
        estado.outraCor = false;
        atualizarCor();
        cores.querySelectorAll(".cf-cor")[PASTEIS.findIndex(([h]) => h === hex)].focus();
      });
      cores.append(amostra);
    }
    const outra = el("button", { type: "button", class: "cf-cor cf-cor-outra", "aria-pressed": String(estado.outraCor), "aria-expanded": String(estado.outraCor), "aria-controls": "cf-outra-cor" }, el("span", { texto: "Outra cor" }));
    outra.addEventListener("click", () => {
      estado.outraCor = true;
      estado.cor = seletorCor.value.toLowerCase();
      atualizarCor();
      seletorCor.focus();
    });
    cores.append(outra);
  }

  function atualizarCor() {
    desenharCores();
    blocoOutraCor.hidden = !estado.outraCor;
    const baixo = contraste(estado.cor, FUNDO_ESCURO) < CONTRASTE_MINIMO;
    avisoCor.replaceChildren();
    if (baixo) avisoCor.append(icone("alerta", "ic-sm"), el("span", { texto: "Essa cor fica difícil de ver no fundo escuro. Prefira um tom mais claro." }));
    desenharPrevia();
  }

  function desenharIcones() {
    icones.replaceChildren();
    const automatico = el(
      "button",
      { type: "button", class: "cf-icone cf-icone-auto", "aria-pressed": String(estado.icone === null), title: "Automático, pelo nome" },
      icone(adivinharIcone(nome.value)),
      el("span", { texto: "Auto" }),
    );
    automatico.setAttribute("aria-label", "Automático, escolhido pelo nome");
    automatico.addEventListener("click", () => escolherIcone(null, automatico));
    icones.append(automatico);
    for (const [id, rotulo] of ICONES) {
      const botao = el("button", { type: "button", class: "cf-icone", "aria-pressed": String(estado.icone === id), "aria-label": rotulo, title: rotulo }, icone(id));
      botao.addEventListener("click", () => escolherIcone(id, botao));
      icones.append(botao);
    }
    notaIcone.textContent = estado.icone === null ? "No automático, o ícone segue o nome. Toque em outro para fixar." : "";
  }

  function escolherIcone(id, botao) {
    estado.icone = id;
    icones.querySelectorAll(".cf-icone").forEach((b) => b.setAttribute("aria-pressed", String(b === botao)));
    notaIcone.textContent = id === null ? "No automático, o ícone segue o nome. Toque em outro para fixar." : "";
    desenharPrevia();
  }

  function marcarNome(texto) {
    erroNome.textContent = texto;
    if (texto) nome.setAttribute("aria-invalid", "true");
    else nome.removeAttribute("aria-invalid");
  }

  const retrato = () => JSON.stringify([nome.value, estado.tipo, estado.cor, estado.icone]);
  const inicial = retrato();
  const podeFechar = () => retrato() === inicial || confirm(editando ? "Descartar as alterações desta categoria?" : "Descartar esta categoria sem salvar?");

  let ultimoAuto = adivinharIcone(nome.value);
  nome.addEventListener("input", () => {
    marcarNome("");
    desenharPrevia();
    const auto = adivinharIcone(nome.value);
    if (auto !== ultimoAuto) {
      ultimoAuto = auto;
      icones.querySelector(".cf-icone-auto svg")?.replaceWith(icone(auto));
    }
  });
  seletorCor.addEventListener("input", () => {
    estado.cor = seletorCor.value.toLowerCase();
    atualizarCor();
  });
  fechar.addEventListener("click", () => {
    if (podeFechar()) dialogo.close();
  });
  dialogo.addEventListener("cancel", (evento) => {
    if (!podeFechar()) evento.preventDefault();
  });
  dialogo.addEventListener("close", () => {
    dialogo.remove();
    if (origemDoFoco?.isConnected) origemDoFoco.focus();
  });

  apagar?.addEventListener("click", async () => {
    if (!confirm(`Apagar a categoria ${categoria.nome}? As transações e contas dela ficam sem categoria. Isso não pode ser desfeito.`)) return;
    mensagem(avisoErro, "erro", "");
    ocupado(apagar, true, "Apagando…");
    try {
      await api.delete(`/categorias/${categoria.id_categoria}`);
      esquecerCategorias();
      esquecerCachesDoFormulario();
      dialogo.close("apagada");
      avisar(`Categoria ${categoria.nome} apagada.`);
      aoApagar?.(categoria);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      mensagem(avisoErro, "erro", erro.message);
    } finally {
      if (dialogo.isConnected) ocupado(apagar, false);
    }
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagem(avisoErro, "erro", "");
    const texto = nome.value.trim();
    if (!texto) {
      marcarNome("Dê um nome para a categoria.");
      return nome.focus();
    }
    const corpo = { nome: texto, tipo_padrao: estado.tipo, cor: estado.cor, icone: estado.icone };
    ocupado(salvar, true, "Salvando…");
    try {
      const salva = editando ? await api.patch(`/categorias/${categoria.id_categoria}`, corpo) : await api.post("/categorias", corpo);
      esquecerCategorias();
      esquecerCachesDoFormulario();
      dialogo.close("salvo");
      avisar(editando ? `Categoria ${salva.nome} atualizada.` : `Categoria ${salva.nome} criada.`);
      aoSalvar?.(salva);
    } catch (erro) {
      if (!(erro instanceof ErroApi)) throw erro;
      if (erro.status === 409) {
        marcarNome("Já existe uma categoria com esse nome, sua ou padrão. Escolha outro.");
        nome.focus();
      } else if (erro.campos.nome) {
        marcarNome("Confira o nome: até 100 caracteres.");
        nome.focus();
      } else {
        mensagem(avisoErro, "erro", erro.message);
      }
    } finally {
      if (dialogo.isConnected) ocupado(salvar, false);
    }
  });

  document.body.append(dialogo);
  desenharTipos();
  atualizarCor();
  desenharIcones();
  dialogo.showModal();
  if (matchMedia("(min-width: 900px)").matches) nome.focus();
  return dialogo;
}
