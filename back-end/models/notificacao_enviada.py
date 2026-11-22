import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

from models.enums import TipoLembrete


class NotificacaoEnviada(Base):
    __tablename__ = "notificacao_enviada"

    id_notificacao_enviada: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_conta_recorrente: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conta_recorrente.id_conta_recorrente", ondelete="CASCADE")
    )
    tipo: Mapped[TipoLembrete] = mapped_column()
    data_referencia: Mapped[date] = mapped_column(Date)
    enviada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "id_conta_recorrente",
            "tipo",
            "data_referencia",
            name="uq_notificacao_enviada_conta_tipo_data",
        ),
    )
