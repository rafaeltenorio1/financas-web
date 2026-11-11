import uuid 

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))