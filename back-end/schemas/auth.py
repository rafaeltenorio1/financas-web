from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from schemas.usuario import normalizar_email


class LoginIn(BaseModel):
    email: Annotated[str, BeforeValidator(normalizar_email), Field(max_length=255)]
    senha: str = Field(max_length=128)


class TrocaSenhaIn(BaseModel):
    senha_atual: str = Field(max_length=128)
    senha_nova: str = Field(min_length=8, max_length=128)


class MensagemOut(BaseModel):
    mensagem: str