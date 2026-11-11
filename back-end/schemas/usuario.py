from pydantic import BaseModel, Field, ConfigDict, EmailStr
import uuid


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    nome: str
    email: EmailStr