import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
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

    @validates("email")
    def validate_email(self, key: str, address: str) -> str:
        return address.strip().lower()

    @property
    def dois_fatores(self) -> bool:
        return self.totp_ativado_em is not None

    @property
    def email_verificado(self) -> bool:
        return self.email_verificado_em is not None
