from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

FUSO = "America/Sao_Paulo"

OFX_SGML = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
ENCODING:USASCII
CHARSET:1252

<OFX>
<BANKMSGSRSV1><STMTTRNRS><STMTRS>
<CURDEF>BRL
<BANKACCTFROM><BANKID>0341<ACCTID>12345-6<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20261110120000[-3:BRT]
<TRNAMT>-50.00
<FITID>FIT001
<MEMO>Padaria São João
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20261105
<TRNAMT>1500,00
<FITID>FIT002
<NAME>SALARIO
<MEMO>EMPRESA &amp; CIA
</STMTTRN>
</BANKTRANLIST>
</STMTRS></STMTTRNRS></BANKMSGSRSV1>
</OFX>
"""

OFX_XML_CARTAO = """<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="220"?>
<OFX><CREDITCARDMSGSRSV1><CCSTMTTRNRS><CCSTMTRS>
<CCACCTFROM><ACCTID>9999</ACCTID></CCACCTFROM>
<BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT</TRNTYPE><DTPOSTED>20261112093000</DTPOSTED><TRNAMT>-89.90</TRNAMT><FITID>C1</FITID><NAME>Livraria</NAME></STMTTRN>
</BANKTRANLIST>
</CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1></OFX>
"""


def _ofx(texto):
    from utils.extratos import ler_ofx

    return ler_ofx(texto, FUSO)


def _csv(texto, mapeamento=None):
    from utils.extratos import ler_csv

    return ler_csv(texto, FUSO, mapeamento)


def _local(*args):
    from zoneinfo import ZoneInfo

    return datetime(*args, tzinfo=ZoneInfo(FUSO))


@pytest.mark.parametrize(
    "conteudo, esperado",
    [
        ("Padaria São João".encode("utf-8"), "Padaria São João"),
        (b"\xef\xbb\xbf" + "Ação".encode("utf-8"), "Ação"),
        ("Padaria São João".encode("cp1252"), "Padaria São João"),
    ],
)
def test_decodifica_utf8_bom_e_windows_1252(conteudo, esperado):
    from utils.extratos import decodificar

    assert decodificar(conteudo) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("1.234,56", Decimal("1234.56")),
        ("1234.56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("-50", Decimal("-50.00")),
        ("(12,34)", Decimal("-12.34")),
        ("R$ 1.500,00", Decimal("1500.00")),
        ("1.234", Decimal("1234.00")),
        ("12,5", Decimal("12.50")),
        ("50,00-", Decimal("-50.00")),
        ("+7.10", Decimal("7.10")),
    ],
)
def test_le_valores_em_varios_formatos(texto, esperado):
    from utils.extratos import ler_valor

    assert ler_valor(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "12,34,56.7.8", "1e5"])
def test_recusa_valor_invalido(texto):
    from utils.extratos import ler_valor

    with pytest.raises(ValueError):
        ler_valor(texto)


def test_detecta_o_formato():
    from utils.extratos import detectar_formato

    assert detectar_formato(OFX_SGML) == "ofx"
    assert detectar_formato(OFX_XML_CARTAO) == "ofx"
    assert detectar_formato("Data;Valor;Descrição\n") == "csv"


def test_ofx_sgml_sem_tags_fechadas():
    primeiro, segundo = _ofx(OFX_SGML)

    assert primeiro.valor == Decimal("-50.00")
    assert primeiro.descricao == "Padaria São João"
    assert primeiro.data_hora == datetime(2026, 11, 10, 12, 0, tzinfo=timezone(timedelta(hours=-3)))
    assert primeiro.id_externo == "ofx:12345-6:FIT001"

    assert segundo.valor == Decimal("1500.00")
    assert segundo.descricao == "SALARIO - EMPRESA & CIA"
    assert segundo.data_hora == _local(2026, 11, 5, 12, 0)
    assert segundo.id_externo == "ofx:12345-6:FIT002"


def test_ofx_xml_de_cartao():
    (lancamento,) = _ofx(OFX_XML_CARTAO)

    assert lancamento.valor == Decimal("-89.90")
    assert lancamento.descricao == "Livraria"
    assert lancamento.data_hora == _local(2026, 11, 12, 9, 30)
    assert lancamento.id_externo == "ofx:9999:C1"


def test_ofx_com_duas_contas_separa_os_ids():
    from utils.extratos import ler_ofx

    texto = OFX_SGML + OFX_SGML.replace("12345-6", "77777-0")
    ids = [l.id_externo for l in ler_ofx(texto, FUSO)]

    assert "ofx:12345-6:FIT001" in ids
    assert "ofx:77777-0:FIT001" in ids


def test_ofx_sem_fitid_usa_hash_estavel():
    texto = OFX_SGML.replace("<FITID>FIT001\n", "").replace("<FITID>FIT002\n", "")

    primeira = [l.id_externo for l in _ofx(texto)]
    segunda = [l.id_externo for l in _ofx(texto)]

    assert primeira == segunda
    assert all(i.startswith("ofx:") and len(i) == 68 for i in primeira)


def test_ofx_sem_lancamentos_e_invalido():
    from utils.extratos import ExtratoInvalido

    with pytest.raises(ExtratoInvalido, match="Nenhum lançamento"):
        _ofx("OFXHEADER:100\n<OFX><BANKTRANLIST></BANKTRANLIST></OFX>")


def test_ofx_com_valor_quebrado_e_invalido():
    from utils.extratos import ExtratoInvalido

    with pytest.raises(ExtratoInvalido, match="Lançamento 1"):
        _ofx(OFX_SGML.replace("<TRNAMT>-50.00", "<TRNAMT>abc"))


def test_csv_padrao_brasileiro():
    texto = "Data;Descrição;Valor\n10/11/2026;Padaria São João;-1.234,56\n05/11/2026 08:15;Salário;5.000,00\n"

    primeiro, segundo = _csv(texto)

    assert primeiro.data_hora == _local(2026, 11, 10, 12, 0)
    assert primeiro.descricao == "Padaria São João"
    assert primeiro.valor == Decimal("-1234.56")
    assert segundo.data_hora == _local(2026, 11, 5, 8, 15)
    assert segundo.valor == Decimal("5000.00")


def test_csv_de_cartao_estilo_nubank():
    texto = "date,title,amount\n2026-11-10,Padaria,12.50\n2026-11-11,Estorno,-12.50\n"

    primeiro, segundo = _csv(texto)

    assert primeiro.descricao == "Padaria"
    assert primeiro.valor == Decimal("12.50")
    assert segundo.valor == Decimal("-12.50")


def test_csv_com_identificador_usa_o_id_do_banco():
    texto = "Data,Valor,Identificador,Descrição\n10/11/2026,-50.00,abc-123,Transferência enviada\n"

    (lancamento,) = _csv(texto)

    assert lancamento.id_externo == "csv:abc-123"


def test_csv_sem_identificador_gera_hash_estavel_e_distingue_repetidos():
    texto = "Data;Descrição;Valor\n10/11/2026;Café;-5,00\n10/11/2026;Café;-5,00\n"

    primeira = [l.id_externo for l in _csv(texto)]
    segunda = [l.id_externo for l in _csv(texto)]

    assert primeira == segunda
    assert primeira[0] != primeira[1]


def test_csv_exportado_pelo_proprio_sistema_volta_igual():
    from utils.exportacao import gerar_csv

    linhas = [
        SimpleNamespace(
            data_local=datetime(2026, 11, 22, 9, 0),
            tipo=SimpleNamespace(value="despesa"),
            nome="=perigoso",
            categoria="Mercado",
            valor=Decimal("1234.50"),
            forma_pagamento=None,
            descricao=None,
            conta_recorrente=None,
        ),
        SimpleNamespace(
            data_local=datetime(2026, 11, 5, 12, 0),
            tipo=SimpleNamespace(value="receita"),
            nome="Salário",
            categoria=None,
            valor=Decimal("5000.00"),
            forma_pagamento=None,
            descricao=None,
            conta_recorrente=None,
        ),
    ]
    from utils.extratos import decodificar

    despesa, receita = _csv(decodificar(gerar_csv(linhas)))

    assert despesa.descricao == "=perigoso"
    assert despesa.valor == Decimal("-1234.50")
    assert despesa.data_hora == _local(2026, 11, 22, 9, 0)
    assert receita.descricao == "Salário"
    assert receita.valor == Decimal("5000.00")


def test_csv_ignora_linhas_vazias_e_valores_zerados():
    texto = "Data;Descrição;Valor\n\n10/11/2026;Saldo anterior;0,00\n11/11/2026;Mercado;-30,00\n;;\n"

    (lancamento,) = _csv(texto)

    assert lancamento.descricao == "Mercado"


def test_csv_com_colunas_desconhecidas_lista_as_colunas():
    from utils.extratos import ExtratoInvalido

    texto = "Quando;Quanto;O quê\n10/11/2026;-30,00;Mercado\n"

    with pytest.raises(ExtratoInvalido) as erro:
        _csv(texto)

    assert erro.value.colunas == ["Quando", "Quanto", "O quê"]


def test_csv_com_mapeamento_informado():
    texto = "Quando;Quanto;O quê\n10/11/2026;-30,00;Mercado\n"

    (lancamento,) = _csv(texto, {"data": "Quando", "valor": "Quanto", "descricao": "O quê"})

    assert lancamento.valor == Decimal("-30.00")
    assert lancamento.descricao == "Mercado"


def test_csv_com_data_invalida_informa_a_linha():
    from utils.extratos import ExtratoInvalido

    texto = "Data;Descrição;Valor\n10/11/2026;Mercado;-30,00\n31/02/2026;Padaria;-5,00\n"

    with pytest.raises(ExtratoInvalido, match="Linha 3: data inválida"):
        _csv(texto)


def test_limite_de_lancamentos():
    from utils.extratos import LIMITE_LANCAMENTOS, ExtratoInvalido

    linhas = "".join(f"10/11/2026;Item {i};-1,00\n" for i in range(LIMITE_LANCAMENTOS + 1))

    with pytest.raises(ExtratoInvalido, match="passa de"):
        _csv("Data;Descrição;Valor\n" + linhas)
