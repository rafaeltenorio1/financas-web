import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

from models.enums import FinalidadeToken


class TokenEmail(Base):
    __tablename__ = "token_email"

    id_token_email: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    finalidade: Mapped[FinalidadeToken] = mapped_column()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    email_novo: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("id_usuario", "finalidade", name="uq_token_email_usuario_finalidade"),
        CheckConstraint("expira_em > criado_em", name="check_token_email_expira_em_maior_que_criado_em"),
        CheckConstraint(
            "(finalidade = 'TROCAR_EMAIL') = (email_novo IS NOT NULL)",
            name="check_token_email_email_novo_so_na_troca",
        ),
    )
