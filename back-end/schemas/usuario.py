from typing import Annotated
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict, EmailStr, StringConstraints
import uuid


def normalizar_email(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v

EmailNormalizado = Annotated[EmailStr, BeforeValidator(normalizar_email)]

NomeUsuario = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]

class UsuarioCreate(BaseModel):
    nome: NomeUsuario
    email: EmailNormalizado
    senha: str = Field(min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    nome: NomeUsuario


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    nome: str
    email: str
    dois_fatores: bool
    email_verificado: bool
