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

export const ICONES = [
  ["c-generica", "Genérico"],
  ["c-moradia", "Casa"],
  ["c-contas", "Energia"],
  ["c-agua", "Água"],
  ["c-gas", "Gás"],
  ["c-wifi", "Internet"],
  ["c-celular", "Celular"],
  ["c-ferramenta", "Ferramenta"],
  ["c-movel", "Móvel"],
  ["c-limpeza", "Limpeza"],
  ["c-carrinho", "Mercado"],
  ["c-cafe", "Café"],
  ["c-alimentacao", "Refeição"],
  ["c-entrega", "Entrega"],
  ["c-transporte", "Carro"],
  ["c-bomba", "Combustível"],
  ["c-estacionamento", "Estacionamento"],
  ["c-onibus", "Ônibus"],
  ["c-aviao", "Avião"],
  ["c-documento", "Documento"],
  ["c-escudo", "Seguro"],
  ["c-saude", "Saúde"],
  ["c-pilula", "Remédio"],
  ["c-dente", "Dente"],
  ["c-conversa", "Conversa"],
  ["c-oculos", "Óculos"],
  ["c-haltere", "Academia"],
  ["c-frasco", "Higiene"],
  ["c-tesoura", "Tesoura"],
  ["c-lazer", "Lazer"],
  ["c-taca", "Festa"],
  ["c-arvore", "Natureza"],
  ["c-controle", "Jogos"],
  ["c-musica", "Música"],
  ["c-assinaturas", "Assinatura"],
  ["c-nuvem", "Nuvem"],
  ["c-notebook", "Computador"],
  ["c-capelo", "Estudo"],
  ["c-livro", "Livro"],
  ["c-pessoas", "Família"],
  ["c-pata", "Pet"],
  ["c-camiseta", "Roupa"],
  ["c-compras", "Compras"],
  ["c-presente", "Presente"],
  ["c-banco", "Banco"],
  ["c-porcento", "Juros"],
  ["c-salario", "Salário"],
  ["c-extra", "Trabalho extra"],
  ["c-grafico", "Investimento"],
  ["c-etiqueta", "Venda"],
  ["c-devolver", "Reembolso"],
];
const ICONES_VALIDOS = new Set(ICONES.map(([id]) => id));

const PALAVRAS = [
  ["c-pata", ["pet", "cachorro", "gato", "racao", "veterinari", "petshop"]],
  ["c-moradia", ["casa", "aluguel", "condominio", "moradia", "apartamento", "iptu", "reforma"]],
  ["c-contas", ["luz", "energia", "eletric"]],
  ["c-agua", ["agua", "esgoto"]],
  ["c-bomba", ["combustivel", "gasolina", "etanol", "posto", "diesel"]],
  ["c-gas", ["gas", "botijao"]],
  ["c-wifi", ["internet", "wifi", "wi-fi", "fibra", "tv a cabo"]],
  ["c-celular", ["celular", "telefone", "chip"]],
  ["c-carrinho", ["mercado", "feira", "hortifruti", "acougue", "atacad"]],
  ["c-cafe", ["cafe", "padaria", "lanche"]],
  ["c-alimentacao", ["restaurante", "comida", "almoco", "jantar", "refeic", "alimenta"]],
  ["c-entrega", ["delivery", "ifood", "entrega"]],
  ["c-estacionamento", ["estacionamento", "pedagio"]],
  ["c-onibus", ["onibus", "metro", "trem", "passagem", "transporte publico"]],
  ["c-transporte", ["carro", "uber", "taxi", "moto", "corrida", "transporte", "veiculo"]],
  ["c-aviao", ["viagem", "viagens", "aviao", "hotel", "hosped", "ferias"]],
  ["c-dente", ["dentista", "odonto"]],
  ["c-pilula", ["farmacia", "remedio", "medicament"]],
  ["c-conversa", ["terapia", "psicolog"]],
  ["c-oculos", ["otica", "optica", "oculos"]],
  ["c-saude", ["saude", "medico", "consulta", "exame", "hospital", "plano de saude"]],
  ["c-haltere", ["academia", "esporte", "futebol", "pilates", "crossfit", "treino"]],
  ["c-frasco", ["higiene", "cosmetic", "perfum", "beleza", "maquiagem"]],
  ["c-tesoura", ["cabelo", "barbe", "salao", "manicure", "unha"]],
  ["c-taca", ["bar", "festa", "cerveja", "bebida", "balada"]],
  ["c-lazer", ["cinema", "teatro", "show", "lazer", "diversao", "ingresso"]],
  ["c-arvore", ["parque", "passeio", "jardim", "planta"]],
  ["c-controle", ["jogo", "game", "hobby", "videogame"]],
  ["c-musica", ["musica", "spotify", "instrumento", "violao", "guitarra", "piano"]],
  ["c-assinaturas", ["assinatura", "streaming", "netflix", "filme", "serie"]],
  ["c-nuvem", ["nuvem", "software", "aplicativo", "app"]],
  ["c-notebook", ["computador", "notebook", "eletronic", "informatica", "tecnologia"]],
  ["c-livro", ["livro", "material escolar", "papelaria", "leitura"]],
  ["c-capelo", ["escola", "faculdade", "curso", "estudo", "educacao", "ingles", "idioma", "mensalidade escolar"]],
  ["c-pessoas", ["filho", "filha", "crianca", "familia", "bebe", "mesada", "pensao", "babá", "baba"]],
  ["c-camiseta", ["roupa", "vestuario", "moda"]],
  ["c-compras", ["compra", "shopping", "loja", "calcado", "sapato", "acessorio"]],
  ["c-presente", ["presente", "doacao", "aniversario", "natal", "dizimo"]],
  ["c-banco", ["banco", "emprestimo", "financiamento", "tarifa", "cartao"]],
  ["c-porcento", ["juros", "multa"]],
  ["c-escudo", ["seguro"]],
  ["c-documento", ["imposto", "taxa", "documento", "ipva", "cartorio", "boleto"]],
  ["c-ferramenta", ["manutencao", "conserto", "reparo", "ferramenta", "oficina"]],
  ["c-movel", ["movel", "moveis", "eletrodomestic", "decoracao"]],
  ["c-limpeza", ["limpeza", "faxina", "diarista", "lavanderia"]],
  ["c-salario", ["salario", "pagamento", "holerite", "pro-labore", "prolabore"]],
  ["c-extra", ["freela", "bico", "extra", "comissao", "bonus"]],
  ["c-grafico", ["investimento", "rendimento", "dividendo", "acoes", "poupanca", "tesouro", "cripto"]],
  ["c-etiqueta", ["venda", "vendas", "brecho"]],
  ["c-devolver", ["reembolso", "estorno", "devolucao", "cashback"]],
];

const semAcento = (texto) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function adivinharIcone(nome) {
  const texto = ` ${semAcento(nome ?? "").replace(/[^a-z0-9]+/g, " ").trim()} `;
  if (!texto.trim()) return "c-generica";
  for (const [simbolo, palavras] of PALAVRAS) {
    if (palavras.some((p) => texto.includes(` ${semAcento(p)}`))) return simbolo;
  }
  return "c-generica";
}

export function iconeValido(id) {
  return ICONES_VALIDOS.has(id);
}

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
  if (iconeValido(cat.icone)) return cat.icone;
  return SIMBOLO_POR_NOME.get(cat.nome) ?? (cat.padrao ? "c-generica" : adivinharIcone(cat.nome));
}

export function corDaCategoria(cat) {
  return cat && ESTILO_COR_VALIDA.test(cat.cor) ? cat.cor : COR_SEM_CATEGORIA;
}
