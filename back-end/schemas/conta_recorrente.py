import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from models.enums import Periodicidade, TipoPagamento, TipoTransacao
from schemas.transacao import TransacaoOut

NomeConta = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class ContaRecorrenteCreate(BaseModel):
    id_categoria: uuid.UUID | None = None
    nome: NomeConta
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    tipo: TipoTransacao
    forma_pagamento: TipoPagamento | None = None
    periodicidade: Periodicidade
    data_inicio: date
    data_fim: date | None = None
    avisar: bool = True
    descricao: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_periodo(self) -> Self:
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")
        return self


class ContaRecorrenteUpdate(BaseModel):
    id_categoria: uuid.UUID | None = None
    nome: NomeConta = Field(default=None)
    valor: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    tipo: TipoTransacao = Field(default=None)
    forma_pagamento: TipoPagamento | None = None
    proximo_vencimento: date = Field(default=None)
    data_fim: date | None = None
    ativa: bool = Field(default=None)
    avisar: bool = Field(default=None)
    descricao: str | None = Field(default=None, max_length=1000)


class ContaRecorrenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_conta_recorrente: uuid.UUID
    id_categoria: uuid.UUID | None
    nome: str
    valor: Decimal
    tipo: TipoTransacao
    forma_pagamento: TipoPagamento | None
    periodicidade: Periodicidade
    data_inicio: date
    proximo_vencimento: date
    data_fim: date | None
    ativa: bool
    avisar: bool
    descricao: str | None
    criada_em: datetime


class PagarIn(BaseModel):
    valor: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    data_hora: AwareDatetime = Field(default=None)
    forma_pagamento: TipoPagamento | None = None
    descricao: str | None = Field(default=None, max_length=1000)


class PagamentoOut(BaseModel):
    transacao: TransacaoOut
    conta: ContaRecorrenteOut
