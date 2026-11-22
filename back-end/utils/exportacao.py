import csv
import io
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

CABECALHO = [
    "Data",
    "Tipo",
    "Nome",
    "Categoria",
    "Valor",
    "Forma de pagamento",
    "Descrição",
    "Conta recorrente",
]
INICIOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r", "\n")
BOM = "﻿"


def proteger_texto(texto: str | None) -> str:
    if not texto:
        return ""
    if texto.startswith(INICIOS_DE_FORMULA):
        return "'" + texto
    return texto


def formatar_valor(valor: Decimal) -> str:
    return f"{valor:.2f}".replace(".", ",")


def formatar_data_hora(data_hora: datetime) -> str:
    return data_hora.strftime("%d/%m/%Y %H:%M")


def gerar_csv(linhas: Iterable) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(CABECALHO)
    for linha in linhas:
        escritor.writerow(
            [
                formatar_data_hora(linha.data_local),
                linha.tipo.value,
                proteger_texto(linha.nome),
                proteger_texto(linha.categoria),
                formatar_valor(linha.valor),
                linha.forma_pagamento.value if linha.forma_pagamento else "",
                proteger_texto(linha.descricao),
                proteger_texto(linha.conta_recorrente),
            ]
        )
    return (BOM + saida.getvalue()).encode("utf-8")
