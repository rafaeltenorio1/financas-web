from pydantic import BaseModel, Field, ConfigDict
import uuid
from models.enums import TipoTransacao


class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    tipo_padrao: TipoTransacao | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: uuid.UUID
    id_usuario: uuid.UUID | None
    nome: str
    tipo_padrao: TipoTransacao | None