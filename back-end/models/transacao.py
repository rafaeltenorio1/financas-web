import uuid 
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Numeric, String,)
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
    recorrente : Mapped[bool] = mapped_column(default=False)
    descricao: Mapped[str | None] = mapped_column(String(1000))

    __table_args__ = (
        CheckConstraint("valor > 0", name="check_valor_positivo"),
    )