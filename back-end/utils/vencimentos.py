import calendar
from datetime import date, timedelta

from models.enums import Periodicidade


def somar_meses(data: date, meses: int, dia: int) -> date:
    total = data.year * 12 + data.month - 1 + meses
    ano, mes = divmod(total, 12)
    mes += 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo_dia))


def calcular_proximo_vencimento(
    atual: date, periodicidade: Periodicidade, data_inicio: date
) -> date:
    if periodicidade is Periodicidade.SEMANAL:
        return atual + timedelta(days=7)
    if periodicidade is Periodicidade.MENSAL:
        return somar_meses(atual, 1, data_inicio.day)
    return somar_meses(atual, 12, data_inicio.day)
