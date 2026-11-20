from typing import Optional

from ..models.filme import Filme
from ..repositories.filmes import FilmeIntegrityConflict, FilmeRepository
from ..schemas.filmes import FilmeCreate, FilmeUpdate


class FilmeNotFoundError(LookupError):
    """Indica que o filme solicitado nao existe."""


class FilmeConflictError(RuntimeError):
    """Indica que o estado atual do filme impede a operacao."""


class FilmeService:
    """Centraliza as regras de negocio do modulo de filmes."""

    def __init__(
        self,
        repository: FilmeRepository,
        *,
        auto_commit: bool = False,
    ):
        """Configura regras de filmes e o controle opcional da transacao."""
        self.repository = repository
        self.auto_commit = auto_commit

    def criar(self, dados: FilmeCreate) -> Filme:
        """Cadastra um filme a partir de dados validados."""
        filme = self.repository.criar(dados.model_dump())
        self._confirmar()
        return filme

    def listar(
        self,
        titulo: Optional[str] = None,
        disponivel: Optional[bool] = None,
    ) -> list[Filme]:
        """Lista filmes usando os filtros informados pela API."""
        return self.repository.listar(titulo=titulo, disponivel=disponivel)

    def buscar_por_id(self, filme_id: int) -> Filme:
        """Retorna um filme ou informa que o recurso nao existe."""
        filme = self.repository.buscar_por_id(filme_id)
        if filme is None:
            raise FilmeNotFoundError('Filme nao encontrado.')
        return filme

    def atualizar(self, filme_id: int, dados: FilmeUpdate) -> Filme:
        """Substitui os dados editaveis de um filme existente."""
        filme = self.buscar_por_id(filme_id)
        filme = self.repository.atualizar(filme, dados.model_dump())
        self._confirmar()
        return filme

    def definir_disponibilidade(self, filme_id: int, disponivel: bool) -> Filme:
        """Atualiza disponibilidade na mesma transacao usada por locacoes."""
        filme = self.buscar_por_id(filme_id)
        if filme.disponivel == disponivel:
            return filme
        filme = self.repository.atualizar(filme, {'disponivel': disponivel})
        self._confirmar()
        return filme

    def excluir(self, filme_id: int) -> None:
        """Exclui somente filme disponivel e sem referencias de locacao."""
        filme = self.buscar_por_id(filme_id)
        if not filme.disponivel:
            raise FilmeConflictError('Nao e possivel excluir um filme alugado.')
        try:
            self.repository.excluir(filme)
        except FilmeIntegrityConflict:
            raise FilmeConflictError(
                'Nao e possivel excluir um filme com locacoes registradas.'
            ) from None
        self._confirmar()

    def _confirmar(self) -> None:
        """Confirma apenas quando o servico controla a transacao HTTP."""
        if self.auto_commit:
            self.repository.confirmar()

