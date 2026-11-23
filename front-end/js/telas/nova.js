import { montar as montarPainel } from "./painel.js";
import { abrirFormularioTransacao } from "../transacao-form.js";
import { recarregar } from "../rotas.js";

export async function montar(raiz, contexto) {
  const desmontar = await montarPainel(raiz, { ...contexto, parametros: new URLSearchParams() });
  abrirFormularioTransacao({
    aoSalvar: () => {
      history.replaceState(null, "", "#/");
      recarregar();
    },
    aoFechar: (salvo) => {
      if (!salvo && location.hash === "#/nova") {
        history.replaceState(null, "", "#/");
        recarregar();
      }
    },
  });
  return desmontar;
}
