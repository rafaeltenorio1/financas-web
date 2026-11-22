from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from schemas.usuario import EmailNormalizado, normalizar_email


class LoginIn(BaseModel):
    email: Annotated[str, BeforeValidator(normalizar_email), Field(max_length=255)]
    senha: str = Field(max_length=128)
    lembrar: bool = False


class TrocaSenhaIn(BaseModel):
    senha_atual: str = Field(max_length=128)
    senha_nova: str = Field(min_length=8, max_length=128)


class ExcluirContaIn(BaseModel):
    senha: str = Field(max_length=128)


class MensagemOut(BaseModel):
    mensagem: str


class CSRFTokenOut(BaseModel):
    csrf_token: str = Field(..., examples=["token_aqui"])

CodigoSegundoFator = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=6, max_length=32)
]


class CodigoIn(BaseModel):
    codigo: CodigoSegundoFator


class SenhaECodigoIn(BaseModel):
    senha: str = Field(max_length=128)
    codigo: CodigoSegundoFator


class Requer2FAOut(BaseModel):
    requer_2fa: Literal[True] = True


class Iniciar2FAOut(BaseModel):
    segredo: str
    uri: str


class CodigosRecuperacaoOut(BaseModel):
    codigos: list[str]


TokenEmailStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class TokenIn(BaseModel):
    token: TokenEmailStr


class EsqueciSenhaIn(BaseModel):
    email: EmailNormalizado


class RedefinirSenhaIn(BaseModel):
    token: TokenEmailStr
    senha_nova: str = Field(min_length=8, max_length=128)


class TrocarEmailIn(BaseModel):
    senha: str = Field(max_length=128)
    codigo: CodigoSegundoFator | None = None
    email_novo: EmailNormalizado
