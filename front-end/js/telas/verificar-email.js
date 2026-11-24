import { telaDeConfirmacao } from "./link-de-email.js";

export const montar = telaDeConfirmacao({
  caminho: "/verificar-email",
  rota: "/auth/verificar-email",
  carregando: "Confirmando seu e-mail",
  sucesso: { titulo: "E-mail confirmado", texto: "Pronto! A partir de agora você recebe os avisos e lembretes da Balancia." },
  invalido: "Este link não vale mais",
  podeReenviar: true,
});
