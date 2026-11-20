from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.filme import Filme


class FilmeIntegrityConflict(RuntimeError):
    """Indica que uma restricao relacional impediu a operacao."""


class FilmeRepository:
    """Concentra as operacoes SQLAlchemy sobre a tabela de filmes."""

    def __init__(self, session: Session):
        """Inicializa o repository com a sessao da unidade de trabalho."""
        self.session = session

    def criar(self, dados: dict) -> Filme:
        """Insere um filme e obtem seu identificador gerado pelo banco."""
        filme = Filme(**dados)
        self.session.add(filme)
        self.session.flush()
        return filme

    def listar(
        self,
        titulo: Optional[str] = None,
        disponivel: Optional[bool] = None,
    ) -> list[Filme]:
        """Lista filmes, opcionalmente por titulo e disponibilidade."""
        statement: Select = select(Filme)
        if titulo:
            termo = self._escapar_like(titulo.strip())
            statement = statement.where(
                Filme.titulo.ilike(f'%{termo}%', escape='\\')
            )
        if disponivel is not None:
            statement = statement.where(Filme.disponivel.is_(disponivel))
        statement = statement.order_by(Filme.id)
        return list(self.session.scalars(statement).all())

    def listar_disponiveis(self) -> list[Filme]:
        """Retorna somente filmes disponiveis para locacao."""
        return self.listar(disponivel=True)

    def buscar_por_id(self, filme_id: int) -> Optional[Filme]:
        """Busca um filme pela chave primaria."""
        return self.session.get(Filme, filme_id)

    def atualizar(self, filme: Filme, dados: dict) -> Filme:
        """Aplica campos validados e sincroniza a alteracao na transacao."""
        for campo, valor in dados.items():
            setattr(filme, campo, valor)
        self.session.flush()
        return filme

    def excluir(self, filme: Filme) -> None:
        """Exclui o filme, respeitando futuras chaves estrangeiras RESTRICT."""
        self.session.delete(filme)
        try:
            self.session.flush()
        except IntegrityError as error:
            raise FilmeIntegrityConflict from error

    def confirmar(self) -> None:
        """Confirma explicitamente a unidade de trabalho atual."""
        self.session.commit()

    @staticmethod
    def _escapar_like(valor: str) -> str:
        """Escapa curingas para que a pesquisa trate o titulo literalmente."""
        return valor.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

