from pydantic import BaseModel, Field, ConfigDict, AwareDatetime
import uuid
from decimal import Decimal
from models.enums import TipoTransacao, TipoPagamento


class TransacaoCreate(BaseModel):
    id_categoria: uuid.UUID | None = Field(default=None)
    nome: str | None = Field(default=None, max_length=255)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    data_hora: AwareDatetime
    tipo: TipoTransacao
    forma_pagamento: TipoPagamento | None = Field(default=None)
    descricao: str | None = Field(default=None, max_length=1000)


class TransacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_transacao: uuid.UUID
    id_categoria: uuid.UUID | None
    nome: str | None
    valor: Decimal
    data_hora: AwareDatetime
    tipo: TipoTransacao
    forma_pagamento: TipoPagamento | None
    id_conta_recorrente: uuid.UUID | None
    id_externo: str | None
    descricao: str | None


class TransacaoUpdate(BaseModel):
    id_categoria: uuid.UUID | None = None
    nome: str | None = Field(default=None, max_length=255)
    valor: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    data_hora: AwareDatetime = Field(default=None)
    tipo: TipoTransacao = Field(default=None)
    forma_pagamento: TipoPagamento | None = None
    descricao: str | None = Field(default=None, max_length=1000)