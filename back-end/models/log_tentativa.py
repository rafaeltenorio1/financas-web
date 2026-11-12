import uuid 
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy import (DateTime, String, func, Index,)
from sqlalchemy.orm import Mapped, mapped_column, validates

from database import Base

class LogTentativa(Base):
    __tablename__ = "log_tentativa"

    id_log_tentativa: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email_tentativa: Mapped[str] = mapped_column(String(255))
    ip: Mapped[IPv4Address | IPv6Address] = mapped_column(INET)
    ocorrida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sucesso: Mapped[bool] = mapped_column()

    @validates("email_tentativa")
    def validate_email(self, key: str, address: str) -> str:
        return address.strip().lower()

    __table_args__ = (
    Index("idx_log_tentativa_email_data", "email_tentativa", "ocorrida_em"),
    Index("idx_log_tentativa_ip_data", "ip", "ocorrida_em"),
    )