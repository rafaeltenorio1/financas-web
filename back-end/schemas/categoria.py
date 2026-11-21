from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict, StringConstraints
import uuid
from models.enums import TipoTransacao

NomeCategoria = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class CategoriaCreate(BaseModel):
    nome: NomeCategoria
    tipo_padrao: TipoTransacao | None = None


class CategoriaUpdate(BaseModel):
    nome: NomeCategoria = Field(default=None)
    tipo_padrao: TipoTransacao | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: uuid.UUID
    nome: str
    tipo_padrao: TipoTransacao | None
    padrao: bool
