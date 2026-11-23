export async function montar(_raiz, { navegar }) {
  navegar("/transacoes?importar=1", { substituir: true });
}
