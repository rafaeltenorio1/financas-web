import { api } from "./api.js";

const SIMBOLOS = {
  "c-moradia": ["Aluguel", "Condomínio", "IPTU", "Seguro Residencial", "Aluguéis Recebidos"],
  "c-contas": ["Energia Elétrica"],
  "c-agua": ["Água e Esgoto", "Lava-jato"],
  "c-gas": ["Gás"],
  "c-wifi": ["Internet/TV"],
  "c-celular": ["Plano de Celular"],
  "c-ferramenta": ["Manutenção e Reparos", "Manutenção do Veículo", "Manutenção de Eletrônicos"],
  "c-movel": ["Móveis e Eletrodomésticos"],
  "c-limpeza": ["Serviços Domésticos"],
  "c-carrinho": ["Supermercado/Feira", "Açougue e Peixaria"],
  "c-cafe": ["Padaria e Cafeteria"],
  "c-alimentacao": ["Restaurantes e Lanchonetes", "Refeição no Trabalho"],
  "c-entrega": ["Delivery"],
  "c-transporte": ["Aplicativos de Corridas"],
  "c-bomba": ["Combustível"],
  "c-estacionamento": ["Estacionamento e Pedágio"],
  "c-documento": ["IPVA e Licenciamento", "Multas de Trânsito", "Imposto de Renda (IRPF)", "Taxas e Documentos", "Restituição do Imposto de Renda"],
  "c-escudo": ["Seguro Auto/Moto"],
  "c-onibus": ["Transporte Público"],
  "c-haltere": ["Academia e Esportes"],
  "c-saude": ["Consultas e Exames", "Plano de Saúde/Odontológico", "Seguro de Vida"],
  "c-dente": ["Dentista"],
  "c-pilula": ["Farmácia e Medicamentos"],
  "c-conversa": ["Terapia e Psicologia"],
  "c-oculos": ["Óptica"],
  "c-frasco": ["Higiene Pessoal", "Cosméticos e Perfumaria"],
  "c-tesoura": ["Barbearia", "Salão"],
  "c-lazer": ["Cinema, Teatro e Shows"],
  "c-taca": ["Bares e Festas"],
  "c-arvore": ["Passeios e Parques"],
  "c-aviao": ["Viagens e Hospedagem"],
  "c-controle": ["Jogos e Hobbies"],
  "c-musica": ["Streaming de Música"],
  "c-assinaturas": ["Streaming de Vídeo"],
  "c-nuvem": ["Nuvem e Softwares"],
  "c-notebook": ["Eletrônicos e Informática"],
  "c-capelo": ["Escola", "Faculdade", "Cursos Livres e Idiomas", "Plataformas de Ensino", "Bolsa e Auxílios"],
  "c-livro": ["Material Escolar e Livros"],
  "c-pessoas": ["Cuidados com Crianças", "Mesada dos Filhos", "Pensão Alimentícia"],
  "c-pata": ["Banho e Tosa", "Ração e Petiscos", "Veterinário e Vacinas"],
  "c-camiseta": ["Roupas"],
  "c-compras": ["Calçados", "Acessórios"],
  "c-presente": ["Presentes e Doações", "Presentes Recebidos"],
  "c-banco": ["Empréstimos e Financiamentos", "Tarifas Bancárias"],
  "c-porcento": ["Juros e Multas"],
  "alerta": ["Imprevistos"],
  "c-salario": ["Salário", "13º Salário", "Adicional de Férias"],
  "c-extra": ["Freelance e Trabalhos Extras"],
  "c-grafico": ["Rendimentos de Investimentos"],
  "c-etiqueta": ["Vendas"],
  "c-devolver": ["Reembolsos"],
};

const SIMBOLO_POR_NOME = new Map(Object.entries(SIMBOLOS).flatMap(([simbolo, nomes]) => nomes.map((nome) => [nome, simbolo])));

export const COR_SEM_CATEGORIA = "var(--cat-outras)";
export const ESTILO_COR_VALIDA = /^#[0-9a-f]{6}$/;

let cache = null;
let pedido = null;

export async function carregarCategorias({ forcar = false } = {}) {
  if (cache && !forcar) return cache;
  pedido ??= api.get("/categorias").then((lista) => {
    cache = new Map(lista.map((c) => [c.id_categoria, c]));
    return cache;
  }).finally(() => (pedido = null));
  return pedido;
}

export function esquecerCategorias() {
  cache = null;
}

export function categoria(id) {
  return id ? cache?.get(id) ?? null : null;
}

export function simboloDaCategoria(cat) {
  if (!cat) return "c-generica";
  return SIMBOLO_POR_NOME.get(cat.nome) ?? "c-generica";
}

export function corDaCategoria(cat) {
  return cat && ESTILO_COR_VALIDA.test(cat.cor) ? cat.cor : COR_SEM_CATEGORIA;
}
