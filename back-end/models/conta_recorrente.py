import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

from models.enums import Periodicidade, TipoPagamento, TipoTransacao


class ContaRecorrente(Base):
    __tablename__ = "conta_recorrente"

    id_conta_recorrente: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    id_categoria: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categoria.id_categoria", ondelete="SET NULL"))
    nome: Mapped[str] = mapped_column(String(255))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tipo: Mapped[TipoTransacao] = mapped_column()
    forma_pagamento: Mapped[TipoPagamento | None] = mapped_column()
    periodicidade: Mapped[Periodicidade] = mapped_column()
    data_inicio: Mapped[date] = mapped_column(Date)
    proximo_vencimento: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)
    ativa: Mapped[bool] = mapped_column(default=True, server_default=true())
    avisar: Mapped[bool] = mapped_column(default=True, server_default=true())
    descricao: Mapped[str | None] = mapped_column(String(1000))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("valor > 0", name="check_conta_recorrente_valor_positivo"),
        CheckConstraint(
            "proximo_vencimento >= data_inicio",
            name="check_conta_recorrente_proximo_depois_do_inicio",
        ),
        CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="check_conta_recorrente_fim_depois_do_inicio",
        ),
        Index("idx_conta_recorrente_id_usuario", "id_usuario"),
    )
