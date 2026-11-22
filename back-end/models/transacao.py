import uuid 
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint,)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

from models.enums import TipoTransacao, TipoPagamento


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
    id_conta_recorrente: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conta_recorrente.id_conta_recorrente", ondelete="SET NULL")
    )
    descricao: Mapped[str | None] = mapped_column(String(1000))
    id_externo: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint("valor > 0", name="check_valor_positivo"),
        UniqueConstraint("id_usuario", "id_externo", name="uq_transacao_usuario_id_externo"),
    )