from datetime import date
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Locacao(Base):
    """Representa uma locacao persistida na tabela relacional `locacoes`.

    `status` e `atrasada` sao derivados de `data_devolucao_real` e da data
    atual; nao sao armazenados no banco.
    """

    __tablename__ = 'locacoes'
    __table_args__ = (
        CheckConstraint(
            'data_devolucao_prevista >= data_locacao',
            name='ck_locacoes_prevista_apos_locacao',
        ),
        CheckConstraint(
            'data_devolucao_real IS NULL OR data_devolucao_real >= data_locacao',
            name='ck_locacoes_real_apos_locacao',
        ),
        # Indice unico parcial: no maximo uma locacao em aberto por filme,
        # enquanto o historico de locacoes devolvidas e ilimitado.
        Index(
            'uq_locacoes_filme_em_aberto',
            'filme_id',
            unique=True,
            postgresql_where=text('data_devolucao_real IS NULL'),
            sqlite_where=text('data_devolucao_real IS NULL'),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('filmes.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    cliente_nome: Mapped[str] = mapped_column(String, nullable=False)
    data_locacao: Mapped[date] = mapped_column(Date, nullable=False)
    data_devolucao_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    data_devolucao_real: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    @property
    def status(self) -> str:
        """Retorna 'Devolvido' quando ha data real; senao 'Em aberto'."""
        return 'Devolvido' if self.data_devolucao_real is not None else 'Em aberto'

    @property
    def atrasada(self) -> bool:
        """Indica locacao ainda aberta cujo prazo previsto ja passou."""
        return (
            self.data_devolucao_real is None
            and self.data_devolucao_prevista < date.today()
        )