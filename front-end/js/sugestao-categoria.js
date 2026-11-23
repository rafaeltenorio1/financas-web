const REGRAS = [
  ["Aplicativos de Corridas", ["uber", "99app", "99 pop", "99pop", "cabify", "indrive"]],
  ["Delivery", ["ifood", "rappi", "ze delivery", "aiqfome", "uber eats", "ubereats"]],
  ["Farmácia e Medicamentos", ["drogasil", "droga raia", "drogaria", "farmacia", "pague menos", "panvel", "drogao"]],
  ["Combustível", ["posto", "shell", "ipiranga", "petrobras", "combustivel", "auto posto"]],
  ["Streaming de Vídeo", ["netflix", "prime video", "disney", "globoplay", "hbo", "max.com", "paramount", "crunchyroll"]],
  ["Streaming de Música", ["spotify", "deezer", "youtube music", "apple music", "tidal"]],
  ["Supermercado/Feira", ["supermercado", "mercado", "carrefour", "pao de acucar", "assai", "atacadao", "hortifruti", "sams club", "dia supermercado", "zaffari", "guanabara"]],
  ["Padaria e Cafeteria", ["padaria", "panificadora", "cafeteria", "starbucks", "cafe"]],
  ["Restaurantes e Lanchonetes", ["restaurante", "lanchonete", "mcdonald", "burger king", "bk ", "habib", "subway", "outback", "giraffas", "pizzaria", "churrascaria"]],
  ["Açougue e Peixaria", ["acougue", "peixaria", "casa de carnes"]],
  ["Energia Elétrica", ["enel", "cemig", "light sa", "copel", "celesc", "coelba", "energia", "neoenergia", "equatorial"]],
  ["Água e Esgoto", ["sabesp", "copasa", "cedae", "embasa", "sanepar", "agua e esgoto"]],
  ["Gás", ["comgas", "ultragaz", "liquigas", "supergasbras"]],
  ["Internet/TV", ["net servicos", "claro net", "vivo fibra", "oi fibra", "sky", "internet"]],
  ["Plano de Celular", ["vivo", "claro", "tim ", "recarga"]],
  ["Academia e Esportes", ["smartfit", "smart fit", "academia", "bluefit", "bodytech", "gympass", "wellhub", "totalpass"]],
  ["Estacionamento e Pedágio", ["estacionamento", "sem parar", "conectcar", "veloe", "pedagio", "estapar"]],
  ["Cinema, Teatro e Shows", ["cinema", "cinemark", "cinepolis", "kinoplex", "ingresso", "sympla", "eventim", "teatro"]],
  ["Tarifas Bancárias", ["tarifa", "anuidade", "cesta de servicos", "manutencao de conta"]],
  ["Juros e Multas", ["iof", "juros", "multa", "encargos"]],
  ["Transporte Público", ["metro", "bilhete unico", "sptrans", "riocard", "onibus", "cptm"]],
  ["Aluguel", ["aluguel"]],
  ["Condomínio", ["condominio"]],
  ["Plataformas de Ensino", ["udemy", "alura", "coursera", "duolingo"]],
  ["Nuvem e Softwares", ["google storage", "google one", "icloud", "dropbox", "microsoft", "adobe", "openai", "notion"]],
  ["Jogos e Hobbies", ["steam", "playstation", "xbox", "nintendo", "epic games"]],
  ["Viagens e Hospedagem", ["airbnb", "booking", "hotel", "latam", "gol linhas", "azul linhas", "decolar", "123milhas"]],
  ["Salário", ["salario", "folha de pagamento", "pagamento de salario", "proventos"]],
  ["Rendimentos de Investimentos", ["rendimento", "rend pago", "dividendo", "juros sobre capital", "cdb", "tesouro direto"]],
  ["Reembolsos", ["reembolso", "estorno", "cashback", "devolucao"]],
  ["Restituição do Imposto de Renda", ["restituicao"]],
];

const normalizar = (texto) =>
  ` ${String(texto ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9.]+/g, " ")
    .trim()} `;

export function criarSugestor(categorias) {
  const porNome = new Map(categorias.map((c) => [normalizar(c.nome).trim(), c]));
  const proprias = categorias.filter((c) => !c.padrao && normalizar(c.nome).trim().length >= 4);
  const regras = REGRAS.map(([nome, chaves]) => [porNome.get(normalizar(nome).trim()), chaves.map((c) => ` ${normalizar(c).trim()}`)]).filter(([cat]) => cat);
  const serve = (cat, tipo) => !cat.tipo_padrao || cat.tipo_padrao === tipo;

  return function sugerir(nome, tipo) {
    const texto = normalizar(nome);
    for (const cat of proprias) {
      if (serve(cat, tipo) && texto.includes(` ${normalizar(cat.nome).trim()}`)) return cat;
    }
    for (const [cat, chaves] of regras) {
      if (serve(cat, tipo) && chaves.some((chave) => texto.includes(chave))) return cat;
    }
    return null;
  };
}
