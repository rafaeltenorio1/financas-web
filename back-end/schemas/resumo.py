import uuid
from decimal import Decimal

from pydantic import BaseModel

from models.enums import TipoTransacao


class ResumoCategoria(BaseModel):
    id_categoria: uuid.UUID | None
    nome: str | None
    tipo: TipoTransacao
    total: Decimal
    quantidade: int


class ResumoMes(BaseModel):
    mes: str
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal


class ResumoOut(BaseModel):
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
    por_categoria: list[ResumoCategoria]
    por_mes: list[ResumoMes]
