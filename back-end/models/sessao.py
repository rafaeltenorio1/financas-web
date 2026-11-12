import uuid 
from datetime import datetime

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, String, func, Index,)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Sessao(Base):
    __tablename__ = "sessao"

    id_sessao: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_acesso_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("expira_em > criada_em", name="check_expira_em_maior_que_criada_em"),
        CheckConstraint("ultimo_acesso_em >= criada_em", name="check_ultimo_acesso_em_maior_ou_igual_a_criada_em"),
        Index("idx_sessao_id_usuario", "id_usuario"),
    )