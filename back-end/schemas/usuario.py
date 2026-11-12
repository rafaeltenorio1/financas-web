from typing import Annotated
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict, EmailStr
import uuid


def normalizar_email(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v

EmailNormalizado = Annotated[EmailStr, BeforeValidator(normalizar_email)]

class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: EmailNormalizado
    senha: str = Field(min_length=8, max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    nome: str
    email: str