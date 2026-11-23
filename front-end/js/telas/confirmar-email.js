import { telaDeConfirmacao } from "./link-de-email.js";

export const montar = telaDeConfirmacao({
  caminho: "/confirmar-email",
  rota: "/auth/trocar-email/confirmar",
  carregando: "Confirmando o e-mail novo",
  sucesso: { titulo: "E-mail trocado", texto: "Use o e-mail novo para entrar daqui em diante. Avisamos o endereço antigo sobre a troca." },
  invalido: "Não foi possível trocar o e-mail",
  podeReenviar: false,
});
