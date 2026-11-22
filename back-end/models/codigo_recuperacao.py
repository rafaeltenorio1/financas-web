import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CodigoRecuperacao(Base):
    __tablename__ = "codigo_recuperacao"

    id_codigo_recuperacao: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    codigo_hash: Mapped[str] = mapped_column(String(64))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("id_usuario", "codigo_hash", name="uq_codigo_recuperacao_usuario_hash"),
    )
