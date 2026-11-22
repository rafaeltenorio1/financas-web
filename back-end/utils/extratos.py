import csv
import hashlib
import html
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from zoneinfo import ZoneInfo

from utils.exportacao import INICIOS_DE_FORMULA

LIMITE_LANCAMENTOS = 5000
TAMANHO_ID_EXTERNO = 255
CENTAVOS = Decimal("0.01")


class ExtratoInvalido(Exception):
    def __init__(self, mensagem: str, colunas: list[str] | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.colunas = colunas


@dataclass(frozen=True)
class Lancamento:
    data_hora: datetime
    valor: Decimal
    descricao: str
    id_externo: str


def decodificar(conteudo: bytes) -> str:
    if conteudo.startswith(b"\xef\xbb\xbf"):
        return conteudo.decode("utf-8-sig")
    try:
        return conteudo.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return conteudo.decode("cp1252")
    except UnicodeDecodeError:
        return conteudo.decode("latin-1")


def detectar_formato(texto: str) -> str:
    inicio = texto[:2000].upper()
    if "OFXHEADER" in inicio or "<OFX>" in texto.upper():
        return "ofx"
    return "csv"


def ler_valor(texto: str) -> Decimal:
    limpo = texto.strip().replace("R$", "").replace("\xa0", "").replace(" ", "")
    negativo = False
    if limpo.startswith("(") and limpo.endswith(")"):
        negativo, limpo = True, limpo[1:-1]
    if limpo.startswith("-"):
        negativo, limpo = True, limpo[1:]
    elif limpo.startswith("+"):
        limpo = limpo[1:]
    if limpo.endswith("-"):
        negativo, limpo = True, limpo[:-1]

    if "," in limpo and "." in limpo:
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", "") if limpo.count(",") > 1 else limpo.replace(",", ".")
    elif "." in limpo and (limpo.count(".") > 1 or len(limpo.rsplit(".", 1)[1]) == 3):
        limpo = limpo.replace(".", "")

    if not re.fullmatch(r"\d+(\.\d+)?", limpo):
        raise ValueError(f"valor inválido: {texto!r}")
    valor = Decimal(limpo).quantize(CENTAVOS, rounding=ROUND_HALF_EVEN)
    return -valor if negativo else valor


def _limitar(id_externo: str, prefixo: str) -> str:
    if len(id_externo) <= TAMANHO_ID_EXTERNO:
        return id_externo
    return f"{prefixo}:{hashlib.sha256(id_externo.encode()).hexdigest()}"


class _GeradorDeHash:
    def __init__(self, prefixo: str):
        self.prefixo = prefixo
        self.ocorrencias: dict[str, int] = {}

    def gerar(self, data_hora: datetime, valor: Decimal, descricao: str) -> str:
        base = f"{data_hora.date().isoformat()}|{valor}|{descricao.strip().lower()}"
        ordem = self.ocorrencias.get(base, 0) + 1
        self.ocorrencias[base] = ordem
        resumo = hashlib.sha256(f"{base}|{ordem}".encode()).hexdigest()
        return f"{self.prefixo}:{resumo}"


def _verificar_limite(lancamentos: list[Lancamento]) -> None:
    if len(lancamentos) > LIMITE_LANCAMENTOS:
        raise ExtratoInvalido(f"O arquivo passa de {LIMITE_LANCAMENTOS} lançamentos.")


def _campo_ofx(bloco: str, tag: str) -> str | None:
    encontrado = re.search(rf"<{tag}>([^<\r\n]*)", bloco, re.IGNORECASE)
    if encontrado is None:
        return None
    valor = html.unescape(encontrado.group(1)).strip()
    return valor or None


def _data_ofx(texto: str, zona: ZoneInfo) -> datetime:
    encontrado = re.fullmatch(
        r"(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2})?)?(?:\.\d+)?"
        r"(?:\[([+-]?\d+(?:\.\d+)?)(?::[^\]]*)?\])?",
        texto.strip(),
    )
    if encontrado is None:
        raise ValueError(f"data inválida: {texto!r}")
    ano, mes, dia, hora, minuto, segundo, deslocamento = encontrado.groups()

    if hora is None:
        resultado = datetime(int(ano), int(mes), int(dia), 12)
    else:
        resultado = datetime(int(ano), int(mes), int(dia), int(hora), int(minuto), int(segundo or 0))

    if deslocamento is not None:
        return resultado.replace(tzinfo=timezone(timedelta(hours=float(deslocamento))))
    return resultado.replace(tzinfo=zona)


def _blocos_de_extrato(texto: str) -> list[str]:
    blocos = re.findall(r"<(?:CC)?STMTRS>(.*?)</(?:CC)?STMTRS>", texto, re.DOTALL | re.IGNORECASE)
    return blocos or [texto]


def _lancamentos_do_bloco(bloco: str) -> list[str]:
    if re.search(r"</STMTTRN>", bloco, re.IGNORECASE):
        return re.findall(r"<STMTTRN>(.*?)</STMTTRN>", bloco, re.DOTALL | re.IGNORECASE)
    return re.split(r"<STMTTRN>", bloco, flags=re.IGNORECASE)[1:]


def ler_ofx(texto: str, fuso: str) -> list[Lancamento]:
    zona = ZoneInfo(fuso)
    lancamentos: list[Lancamento] = []
    hashes = _GeradorDeHash("ofx")

    for bloco in _blocos_de_extrato(texto):
        conta = _campo_ofx(bloco, "ACCTID") or ""
        for numero, transacao in enumerate(_lancamentos_do_bloco(bloco), start=1):
            data_texto = _campo_ofx(transacao, "DTPOSTED")
            valor_texto = _campo_ofx(transacao, "TRNAMT")
            if data_texto is None or valor_texto is None:
                raise ExtratoInvalido(f"Lançamento {numero} sem data ou valor.")
            try:
                data_hora = _data_ofx(data_texto, zona)
                valor = ler_valor(valor_texto)
            except ValueError:
                raise ExtratoInvalido(f"Lançamento {numero} com data ou valor inválido.")
            if valor == 0:
                continue

            partes = [_campo_ofx(transacao, "NAME"), _campo_ofx(transacao, "MEMO")]
            descricao = " - ".join(dict.fromkeys(p for p in partes if p)) or "Sem descrição"

            fitid = _campo_ofx(transacao, "FITID")
            if fitid:
                id_externo = _limitar(f"ofx:{conta}:{fitid}", "ofx")
            else:
                id_externo = hashes.gerar(data_hora, valor, descricao)

            lancamentos.append(Lancamento(data_hora, valor, descricao, id_externo))
            _verificar_limite(lancamentos)

    if not lancamentos:
        raise ExtratoInvalido("Nenhum lançamento encontrado no arquivo.")
    return lancamentos


NOMES_DATA = {"data", "date", "data lancamento", "data do lancamento", "data da compra", "dt"}
NOMES_DESCRICAO = {
    "descricao", "description", "historico", "title", "titulo",
    "nome", "estabelecimento", "lancamento", "memo",
}
NOMES_VALOR = {"valor", "amount", "valor (r$)", "valor r$", "quantia", "value"}
NOMES_IDENTIFICADOR = {"identificador", "id", "codigo", "fitid"}
NOMES_TIPO = {"tipo", "type", "natureza", "d/c"}
TIPOS_SAIDA = {"despesa", "debito", "d", "saida"}
TIPOS_ENTRADA = {"receita", "credito", "c", "entrada"}
FORMATOS_DATA = [
    ("%d/%m/%Y %H:%M:%S", True),
    ("%d/%m/%Y %H:%M", True),
    ("%d/%m/%Y", False),
    ("%d/%m/%y", False),
    ("%d-%m-%Y", False),
    ("%Y-%m-%d %H:%M:%S", True),
    ("%Y-%m-%d", False),
]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.strip().strip('"').lower()


def _data_csv(texto: str, zona: ZoneInfo) -> datetime:
    texto = texto.strip()
    for formato, tem_hora in FORMATOS_DATA:
        try:
            resultado = datetime.strptime(texto, formato)
        except ValueError:
            continue
        if not tem_hora:
            resultado = resultado.replace(hour=12)
        return resultado.replace(tzinfo=zona)

    resultado = datetime.fromisoformat(texto)
    if resultado.tzinfo is None:
        return resultado.replace(tzinfo=zona)
    return resultado


def _texto_csv(texto: str | None) -> str:
    texto = (texto or "").strip()
    if texto.startswith("'") and texto[1:2] and texto[1] in INICIOS_DE_FORMULA:
        return texto[1:]
    return texto


def _separador(primeira_linha: str) -> str:
    return max([";", ",", "\t"], key=primeira_linha.count)


def _achar_coluna(colunas: dict[str, str], nomes: set[str], escolhida: str | None) -> str | None:
    if escolhida is not None:
        return colunas.get(_normalizar(escolhida))
    for normalizado, original in colunas.items():
        if normalizado in nomes:
            return original
    return None


def ler_csv(texto: str, fuso: str, mapeamento: dict | None = None) -> list[Lancamento]:
    zona = ZoneInfo(fuso)
    linhas_texto = texto.splitlines()
    if not linhas_texto:
        raise ExtratoInvalido("O arquivo está vazio.")

    leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=_separador(linhas_texto[0]))
    cabecalho = next(leitor, [])
    colunas = {_normalizar(nome): nome for nome in cabecalho if nome.strip()}
    mapeamento = mapeamento or {}

    col_data = _achar_coluna(colunas, NOMES_DATA, mapeamento.get("data"))
    col_valor = _achar_coluna(colunas, NOMES_VALOR, mapeamento.get("valor"))
    col_descricao = _achar_coluna(colunas, NOMES_DESCRICAO, mapeamento.get("descricao"))
    col_id = _achar_coluna(colunas, NOMES_IDENTIFICADOR, mapeamento.get("identificador"))
    col_tipo = None if mapeamento else _achar_coluna(colunas, NOMES_TIPO, None)

    if col_data is None or col_valor is None or col_descricao is None:
        raise ExtratoInvalido(
            "Não reconhecemos as colunas de data, valor e descrição. Indique quais são.",
            colunas=[nome for nome in cabecalho if nome.strip()],
        )

    indice = {nome: posicao for posicao, nome in enumerate(cabecalho)}
    hashes = _GeradorDeHash("csv")
    lancamentos: list[Lancamento] = []

    for numero, linha in enumerate(leitor, start=2):
        if not any(celula.strip() for celula in linha):
            continue

        def celula(coluna: str | None) -> str:
            if coluna is None or indice[coluna] >= len(linha):
                return ""
            return linha[indice[coluna]]

        try:
            data_hora = _data_csv(celula(col_data), zona)
        except ValueError:
            raise ExtratoInvalido(f"Linha {numero}: data inválida.")
        try:
            valor = ler_valor(celula(col_valor))
        except ValueError:
            raise ExtratoInvalido(f"Linha {numero}: valor inválido.")
        if valor == 0:
            continue

        tipo = _normalizar(celula(col_tipo))
        if tipo in TIPOS_SAIDA:
            valor = -abs(valor)
        elif tipo in TIPOS_ENTRADA:
            valor = abs(valor)

        descricao = _texto_csv(celula(col_descricao)) or "Sem descrição"
        identificador = celula(col_id).strip()
        if identificador:
            id_externo = _limitar(f"csv:{identificador}", "csv")
        else:
            id_externo = hashes.gerar(data_hora, valor, descricao)

        lancamentos.append(Lancamento(data_hora, valor, descricao, id_externo))
        _verificar_limite(lancamentos)

    if not lancamentos:
        raise ExtratoInvalido("Nenhum lançamento encontrado no arquivo.")
    return lancamentos
