import uuid 

from sqlalchemy import (CheckConstraint, ForeignKey, String, UniqueConstraint,)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

from models.enums import TipoTransacao 


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    tipo_padrao: Mapped[TipoTransacao | None] = mapped_column()
    nome: Mapped[str] = mapped_column(String(100))
    cor: Mapped[str] = mapped_column(String(7), default="#7dbde8", server_default="#7dbde8")
    icone: Mapped[str | None] = mapped_column(String(40))

    @property
    def padrao(self) -> bool:
        return self.id_usuario is None

    __table_args__ = (
        UniqueConstraint("id_usuario", "nome", name="uq_categoria_usuario_nome", postgresql_nulls_not_distinct=True,),
        CheckConstraint("cor ~ '^#[0-9a-f]{6}$'", name="check_categoria_cor_hex"),
        CheckConstraint("icone ~ '^c-[a-z0-9-]{1,38}$'", name="check_categoria_icone"),
    )