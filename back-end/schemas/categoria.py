from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, ConfigDict, StringConstraints
import uuid
from models.enums import TipoTransacao

NomeCategoria = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]

CorHex = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^#[0-9a-fA-F]{6}$"),
    AfterValidator(str.lower),
]


class CategoriaCreate(BaseModel):
    nome: NomeCategoria
    tipo_padrao: TipoTransacao | None = None
    cor: CorHex | None = None


class CategoriaUpdate(BaseModel):
    nome: NomeCategoria = Field(default=None)
    tipo_padrao: TipoTransacao | None = None
    cor: CorHex = Field(default=None)


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: uuid.UUID
    nome: str
    tipo_padrao: TipoTransacao | None
    cor: str
    padrao: bool
