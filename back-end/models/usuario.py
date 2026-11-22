import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, true
from sqlalchemy.orm import Mapped, mapped_column, validates

from database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    totp_segredo: Mapped[str | None] = mapped_column(String(255))
    totp_ativado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    totp_ultimo_passo: Mapped[int | None] = mapped_column(BigInteger)
    email_verificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fuso: Mapped[str] = mapped_column(
        String(64), default="America/Sao_Paulo", server_default="America/Sao_Paulo"
    )
    lembrete_dias_antes: Mapped[int] = mapped_column(default=1, server_default="1")
    lembrete_no_dia: Mapped[bool] = mapped_column(default=True, server_default=true())
    lembrete_atraso: Mapped[bool] = mapped_column(default=True, server_default=true())

    __table_args__ = (
        CheckConstraint(
            "lembrete_dias_antes BETWEEN 0 AND 7", name="check_usuario_lembrete_dias_antes"
        ),
    )

    @validates("email")
    def validate_email(self, key: str, address: str) -> str:
        return address.strip().lower()

    @property
    def dois_fatores(self) -> bool:
        return self.totp_ativado_em is not None

    @property
    def email_verificado(self) -> bool:
        return self.email_verificado_em is not None
