from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict, EmailStr, StringConstraints, field_validator
import uuid


def normalizar_email(v: str) -> str:
    if isinstance(v, str):
        return v.strip().lower()
    return v

EmailNormalizado = Annotated[EmailStr, BeforeValidator(normalizar_email)]

NomeUsuario = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]

CartaoId = Literal["saldo", "transacoes", "categorias", "origem", "meses", "numeros", "contas"]
NumeroId = Literal[
    "previsao", "pagar", "media", "credito", "fixos", "maior",
    "guardado", "quantidade", "assinaturas", "media12",
]


class CartaoPainel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CartaoId
    largura: Literal["estreito", "largo", "inteiro"]


class PreferenciasPainel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cartoes: list[CartaoPainel] = Field(max_length=7)
    numeros: list[NumeroId] = Field(max_length=10)
    periodo_meses: Literal[2, 3, 12]
    lista_transacoes: Literal["lista", "colunas"]

    @field_validator("cartoes")
    @classmethod
    def cartoes_sem_repeticao(cls, cartoes: list[CartaoPainel]) -> list[CartaoPainel]:
        ids = [c.id for c in cartoes]
        if len(ids) != len(set(ids)):
            raise ValueError("cartão repetido")
        return cartoes

    @field_validator("numeros")
    @classmethod
    def numeros_sem_repeticao(cls, numeros: list[str]) -> list[str]:
        if len(numeros) != len(set(numeros)):
            raise ValueError("número repetido")
        return numeros


class UsuarioCreate(BaseModel):
    nome: NomeUsuario
    email: EmailNormalizado
    senha: str = Field(min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    nome: NomeUsuario = Field(default=None)
    fuso: str = Field(default=None, min_length=1, max_length=64)
    lembrete_dias_antes: int = Field(default=None, ge=0, le=7)
    lembrete_no_dia: bool = Field(default=None)
    lembrete_atraso: bool = Field(default=None)
    resumo_mensal: bool = Field(default=None)
    preferencias_painel: PreferenciasPainel | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: uuid.UUID
    nome: str
    email: str
    dois_fatores: bool
    email_verificado: bool
    fuso: str
    lembrete_dias_antes: int
    lembrete_no_dia: bool
    lembrete_atraso: bool
    resumo_mensal: bool
    preferencias_painel: dict | None
