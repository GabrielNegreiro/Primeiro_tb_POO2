from sqlalchemy import Boolean, CheckConstraint, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Filme(Base):
    """Representa um filme persistido na tabela relacional `filmes`."""

    __tablename__ = 'filmes'
    __table_args__ = (
        CheckConstraint('ano >= 1888', name='ck_filmes_ano_minimo'),
        CheckConstraint('duracao > 0', name='ck_filmes_duracao_positiva'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    genero: Mapped[str] = mapped_column(String(100), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    duracao: Mapped[int] = mapped_column(Integer, nullable=False)
    disponivel: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )

