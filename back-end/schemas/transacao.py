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
    recorrente : bool = Field(default=False)
    descricao: str | None = Field(default=None, max_length=1000)


class TransacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_transacao: uuid.UUID
    id_usuario: uuid.UUID
    id_categoria: uuid.UUID | None
    nome: str | None
    valor: Decimal
    data_hora: AwareDatetime
    tipo: TipoTransacao
    forma_pagamento: TipoPagamento | None
    recorrente : bool
    descricao: str | None