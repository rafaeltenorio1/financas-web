from datetime import date

import pytest


def _proximo(atual, periodicidade, inicio=None):
    from models.enums import Periodicidade
    from utils.vencimentos import calcular_proximo_vencimento

    return calcular_proximo_vencimento(atual, Periodicidade[periodicidade], inicio or atual)


@pytest.mark.parametrize(
    "atual, esperado",
    [
        (date(2026, 11, 10), date(2026, 12, 10)),
        (date(2026, 12, 10), date(2027, 1, 10)),
        (date(2026, 1, 15), date(2026, 2, 15)),
    ],
)
def test_mensal_simples(atual, esperado):
    assert _proximo(atual, "MENSAL") == esperado


def test_mensal_dia_31_encurta_e_depois_volta():
    inicio = date(2027, 1, 31)

    fevereiro = _proximo(inicio, "MENSAL", inicio)
    marco = _proximo(fevereiro, "MENSAL", inicio)
    abril = _proximo(marco, "MENSAL", inicio)

    assert fevereiro == date(2027, 2, 28)
    assert marco == date(2027, 3, 31)
    assert abril == date(2027, 4, 30)


def test_mensal_dia_31_em_ano_bissexto():
    inicio = date(2028, 1, 31)
    assert _proximo(inicio, "MENSAL", inicio) == date(2028, 2, 29)


def test_anual_29_de_fevereiro():
    inicio = date(2028, 2, 29)

    seguintes = [inicio]
    for _ in range(4):
        seguintes.append(_proximo(seguintes[-1], "ANUAL", inicio))

    assert seguintes[1:] == [
        date(2029, 2, 28),
        date(2030, 2, 28),
        date(2031, 2, 28),
        date(2032, 2, 29),
    ]


def test_anual_simples():
    assert _proximo(date(2026, 11, 22), "ANUAL") == date(2027, 11, 22)


def test_semanal_atravessa_mes_e_ano():
    assert _proximo(date(2026, 12, 29), "SEMANAL") == date(2027, 1, 5)
