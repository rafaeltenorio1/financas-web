import { el } from "../../dom.js";
import { dataCurta, moeda } from "../../formatos.js";
import { contasDoMes } from "../calculos.js";
import { cabecalho, link, vazio } from "../componentes.js";

function quando(conta) {
  const data = dataCurta(`${conta.proximo_vencimento}T12:00:00Z`);
  if (conta.dias < 0) return [`atrasada há ${-conta.dias} ${conta.dias === -1 ? "dia" : "dias"}, ${data}`, "atrasada"];
  if (conta.dias === 0) return ["vence hoje", "perto"];
  if (conta.dias === 1) return ["vence amanhã", "perto"];
  return [`vence em ${conta.dias} dias, ${data}`, conta.dias <= 7 ? "perto" : ""];
}

export default {
  id: "contas",
  titulo: "Próximas contas",
  montar(cartao, { dados, contextoAtual }) {
    cabecalho(cartao, "Próximas contas", link("Ver contas", "#/contas", "Ver todas as contas recorrentes"));
    const contas = contasDoMes(dados.contas, contextoAtual).slice(0, 5);
    if (!contas.length) {
      cartao.append(vazio("Nenhuma conta recorrente ativa.", { href: "#/contas", texto: "Cadastrar conta" }));
      return;
    }
    const lista = el("ul", { class: "contas" });
    for (const conta of contas) {
      const [texto, classe] = quando(conta);
      lista.append(
        el(
          "li",
          {},
          el("span", { class: "conta-nome", texto: conta.nome }),
          el("span", { class: "conta-valor num", texto: moeda(conta.valor) }),
          el("span", { class: `conta-quando ${classe}`, texto }),
        ),
      );
    }
    cartao.append(lista);
  },
};
