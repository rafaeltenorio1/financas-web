const partesCache = new Map();

function partes(ms, fuso) {
  if (!partesCache.has(fuso)) {
    partesCache.set(
      fuso,
      new Intl.DateTimeFormat("en-US", {
        timeZone: fuso,
        hourCycle: "h23",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
    );
  }
  const valores = Object.fromEntries(partesCache.get(fuso).formatToParts(new Date(ms)).map((p) => [p.type, p.value]));
  return {
    ano: Number(valores.year),
    mes: Number(valores.month),
    dia: Number(valores.day),
    hora: Number(valores.hour),
    minuto: Number(valores.minute),
    segundo: Number(valores.second),
  };
}

function deslocamento(ms, fuso) {
  const p = partes(ms, fuso);
  return Date.UTC(p.ano, p.mes - 1, p.dia, p.hora, p.minuto, p.segundo) - Math.floor(ms / 1000) * 1000;
}

export function inicioDoMes({ ano, mes }, fuso) {
  const local = Date.UTC(ano, mes - 1, 1);
  const primeira = local - deslocamento(local, fuso);
  return new Date(local - deslocamento(primeira, fuso));
}

export function hoje(fuso) {
  const p = partes(Date.now(), fuso);
  return { ano: p.ano, mes: p.mes, dia: p.dia };
}

export function somarMeses({ ano, mes }, quantidade) {
  const total = ano * 12 + (mes - 1) + quantidade;
  return { ano: Math.floor(total / 12), mes: (total % 12) + 1 };
}

export function compararMeses(a, b) {
  return a.ano * 12 + a.mes - (b.ano * 12 + b.mes);
}

export function chaveDoMes({ ano, mes }) {
  return `${ano}-${String(mes).padStart(2, "0")}`;
}

export function lerChaveDoMes(texto) {
  const achado = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(texto || "");
  return achado ? { ano: Number(achado[1]), mes: Number(achado[2]) } : null;
}

export function diasNoMes({ ano, mes }) {
  return new Date(Date.UTC(ano, mes, 0)).getUTCDate();
}

export function chaveDoDia({ ano, mes, dia }) {
  return `${chaveDoMes({ ano, mes })}-${String(dia).padStart(2, "0")}`;
}

export function diasEntre(deIso, ateIso) {
  const [a, b] = [deIso, ateIso].map((d) => Date.UTC(...d.split("-").map((n, i) => Number(n) - (i === 1 ? 1 : 0))));
  return Math.round((b - a) / 86400000);
}
