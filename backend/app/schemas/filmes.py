from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ANO_MINIMO = 1888
ANO_MAXIMO = date.today().year + 1

TituloFilme = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
GeneroFilme = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class FilmeBase(BaseModel):
    """Campos e validacoes compartilhados pelos contratos de filme."""

    model_config = ConfigDict(extra='forbid')

    titulo: TituloFilme
    genero: GeneroFilme
    ano: int = Field(ge=ANO_MINIMO, le=ANO_MAXIMO)
    duracao: int = Field(gt=0)
    disponivel: bool = True


class FilmeCreate(FilmeBase):
    """Corpo aceito por POST /filmes; o id e gerado pelo banco."""


class FilmeUpdate(FilmeBase):
    """Corpo completo aceito por PUT /filmes/{id}."""


class FilmeResponse(FilmeBase):
    """Representacao publica serializada a partir do model SQLAlchemy."""

    model_config = ConfigDict(from_attributes=True)

    id: int

