// Dados de EXEMPLO. Quando a API existir, troque por fetch() ao back-end.
const transacoes = [
  { id: 1, descricao: "Salário", categoria: "Renda", valor: 3200.0, data: "2026-11-05" },
  { id: 2, descricao: "Aluguel", categoria: "Moradia", valor: -950.0, data: "2026-11-05" },
  { id: 3, descricao: "Supermercado", categoria: "Alimentação", valor: -312.4, data: "2026-11-06" },
  { id: 4, descricao: "Internet", categoria: "Contas", valor: -99.9, data: "2026-11-07" },
  { id: 5, descricao: "Freelance", categoria: "Renda", valor: 450.0, data: "2026-11-08" },
  { id: 6, descricao: "Ônibus", categoria: "Transporte", valor: -48.0, data: "2026-11-08" },
  { id: 7, descricao: "Restaurante", categoria: "Alimentação", valor: -76.5, data: "2026-11-09" },
];

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const dataCurta = (iso) =>
  new Date(iso + "T00:00:00").toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });

function renderResumo(lista) {
  const ganhos = lista.filter((t) => t.valor > 0).reduce((s, t) => s + t.valor, 0);
  const gastos = lista.filter((t) => t.valor < 0).reduce((s, t) => s + t.valor, 0);
  document.getElementById("ganhos").textContent = brl.format(ganhos);
  document.getElementById("gastos").textContent = brl.format(Math.abs(gastos));
  document.getElementById("saldo").textContent = brl.format(ganhos + gastos);
}

function renderLista(lista) {
  const ul = document.getElementById("lista");
  ul.innerHTML = "";
  [...lista].sort((a, b) => b.data.localeCompare(a.data) || b.id - a.id).forEach((t) => {
    const li = document.createElement("li");
    li.className = "tx";

    const icone = document.createElement("div");
    icone.className = "tx-icon";
    icone.textContent = t.descricao.slice(0, 2).toUpperCase();

    const info = document.createElement("div");
    const nome = document.createElement("div");
    nome.className = "tx-name";
    nome.textContent = t.descricao;
    const meta = document.createElement("div");
    meta.className = "tx-meta";
    meta.textContent = `${t.categoria}, ${dataCurta(t.data)}`;
    info.append(nome, meta);

    const valor = document.createElement("div");
    valor.className = "tx-amount " + (t.valor >= 0 ? "is-in" : "is-out");
    valor.textContent = (t.valor >= 0 ? "+" : "-") + brl.format(Math.abs(t.valor));

    li.append(icone, info, valor);
    ul.append(li);
  });
}

function renderGrafico(lista) {
  const svg = document.getElementById("grafico");
  const porDia = {};
  lista.filter((t) => t.valor < 0).forEach((t) => {
    porDia[t.data] = (porDia[t.data] || 0) + Math.abs(t.valor);
  });
  const dias = Object.keys(porDia).sort();
  if (dias.length < 2) { svg.innerHTML = ""; return; }

  const W = 600, H = 180, pad = 16;
  const max = Math.max(...Object.values(porDia));
  const pts = dias.map((d, i) => [
    pad + (i * (W - 2 * pad)) / (dias.length - 1),
    H - pad - (porDia[d] / max) * (H - 2 * pad),
  ]);
  const linha = pts.map((p) => p.join(",")).join(" ");
  const area = `${pad},${H - pad} ${linha} ${W - pad},${H - pad}`;

  svg.innerHTML =
    `<polygon class="chart-area" points="${area}"/>` +
    `<polyline class="chart-line" points="${linha}"/>` +
    pts.map((p) => `<circle class="chart-dot" cx="${p[0]}" cy="${p[1]}" r="4"/>`).join("");
}

renderResumo(transacoes);
renderLista(transacoes);
renderGrafico(transacoes);