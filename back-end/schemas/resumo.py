import uuid
from decimal import Decimal

from pydantic import BaseModel

from models.enums import TipoPagamento, TipoTransacao
from schemas.transacao import TransacaoOut


class ResumoCategoria(BaseModel):
    id_categoria: uuid.UUID | None
    nome: str | None
    cor: str | None
    tipo: TipoTransacao
    total: Decimal
    quantidade: int


class ResumoMes(BaseModel):
    mes: str
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
    categorias: list[ResumoCategoria]


class ResumoFormaPagamento(BaseModel):
    forma_pagamento: TipoPagamento | None
    tipo: TipoTransacao
    total: Decimal
    quantidade: int


class ResumoOut(BaseModel):
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
    despesas_fixas: Decimal
    maior_despesa: TransacaoOut | None
    por_categoria: list[ResumoCategoria]
    por_forma_pagamento: list[ResumoFormaPagamento]
    por_mes: list[ResumoMes]
