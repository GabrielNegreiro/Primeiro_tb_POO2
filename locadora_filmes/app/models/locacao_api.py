from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.models.filme import Filme


@dataclass
class LocacaoApi:
    """Locacao confirmada pela API, com a interface da locacao legada."""

    id: int
    filme_id: int
    cliente_nome: str
    data_locacao: date
    data_devolucao_prevista: date
    data_devolucao_real: Optional[date]
    status: str
    atrasada: bool
    # Associado pelo identificador a partir do cache de filmes; None quando o
    # filme ainda nao foi carregado.
    filme: Optional[Filme] = field(default=None, compare=False, repr=False)

    @property
    def titulo_filme(self) -> str:
        """Titulo do filme, ou um rotulo seguro quando ele nao esta no cache."""
        if self.filme is not None:
            return self.filme.titulo
        return f'Filme #{self.filme_id} (nao carregado)'


def titulo_do_filme(locacao) -> str:
    """Titulo exibivel para locacoes da API ou do modulo legado."""
    titulo = getattr(locacao, 'titulo_filme', None)
    if isinstance(titulo, str):
        return titulo
    return locacao.filme.titulo