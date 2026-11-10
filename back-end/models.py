import uuid 
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint,)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TipoTransacao(enum.Enum):
    RECEITA = "ganho"
    DESPESA = "perda"


class TipoPagamento(enum.Enum):
    PIX = "pix"
    CARTAO_CREDITO = "credito"
    CARTAO_DEBITO = "debito"
    BOLETO = "boleto"
    DINHEIRO = "dinheiro"


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))


class Transacao(Base):
    __tablename__ = "transacao"

    id_transacao: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    id_categoria: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categoria.id_categoria", ondelete="SET NULL"))
    nome: Mapped[str | None] = mapped_column(String(255))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tipo: Mapped[TipoTransacao] = mapped_column()
    forma_pagamento: Mapped[TipoPagamento | None] = mapped_column()
    recorrente : Mapped[bool] = mapped_column(default=False)
    descricao: Mapped[str | None] = mapped_column(String(1000))

    __table_args__ = (
        CheckConstraint("valor > 0", name="check_valor_positivo"),
    )


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    tipo_padrao: Mapped[TipoTransacao | None] = mapped_column()
    nome: Mapped[str] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint("id_usuario", "nome", name="uq_categoria_usuario_nome", postgresql_nulls_not_distinct=True,),
    )