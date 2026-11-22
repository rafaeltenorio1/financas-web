import uuid
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from models.enums import TipoPagamento, TipoTransacao

TAMANHO_MAXIMO_ARQUIVO = 2 * 1024 * 1024
TAMANHO_MAXIMO_BASE64 = 4 * ((TAMANHO_MAXIMO_ARQUIVO + 2) // 3) + 100


class MapeamentoCsvIn(BaseModel):
    data: str = Field(min_length=1, max_length=100)
    valor: str = Field(min_length=1, max_length=100)
    descricao: str = Field(min_length=1, max_length=100)
    identificador: str | None = Field(default=None, max_length=100)


class PreviaIn(BaseModel):
    arquivo_base64: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_BASE64)
    inverter_sinal: bool = False
    mapeamento: MapeamentoCsvIn | None = None


class ItemPrevia(BaseModel):
    data_hora: AwareDatetime
    valor: Decimal
    tipo: TipoTransacao
    nome: str
    id_externo: str
    duplicada: bool


class PreviaOut(BaseModel):
    formato: Literal["ofx", "csv"]
    total: int
    duplicadas: int
    itens: list[ItemPrevia]


class ItemImportacao(BaseModel):
    data_hora: AwareDatetime
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    tipo: TipoTransacao
    nome: str | None = Field(default=None, max_length=255)
    id_categoria: uuid.UUID | None = None
    forma_pagamento: TipoPagamento | None = None
    descricao: str | None = Field(default=None, max_length=1000)
    id_externo: str = Field(min_length=1, max_length=255)


class ImportacaoIn(BaseModel):
    itens: list[ItemImportacao] = Field(min_length=1, max_length=5000)


class ImportacaoOut(BaseModel):
    criadas: int
    ignoradas: int
