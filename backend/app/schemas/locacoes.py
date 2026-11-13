from datetime import date
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

# Nome do cliente: remove espacos nas pontas e nao aceita vazio.
NomeCliente = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


def _validar_ordem_das_datas(data_locacao, data_devolucao_prevista, data_devolucao_real):
    if data_devolucao_prevista is not None and data_devolucao_prevista < data_locacao:
        raise ValueError(
            'A data de devolucao prevista nao pode ser anterior a data da locacao.'
        )
    if data_devolucao_real is not None and data_devolucao_real < data_locacao:
        raise ValueError(
            'A data de devolucao real nao pode ser anterior a data da locacao.'
        )


class FiltroLocacao(str, Enum):
    """Filtro de GET /locacoes: espelha listar_todas, listar_ativas e listar_atrasadas."""

    TODAS = 'todas'
    ATIVAS = 'ativas'
    ATRASADAS = 'atrasadas'


class LocacaoCreate(BaseModel):
    """Corpo de POST /locacoes. O id e gerado pelo banco, nunca enviado."""

    model_config = ConfigDict(extra='forbid')

    filme_id: int = Field(gt=0)
    cliente_nome: NomeCliente
    data_locacao: date = Field(default_factory=date.today)
    data_devolucao_prevista: date

    @model_validator(mode='after')
    def _datas_em_ordem(self):
        _validar_ordem_das_datas(
            self.data_locacao, self.data_devolucao_prevista, None
        )
        return self


class LocacaoUpdate(BaseModel):
    """Corpo de PUT /locacoes/{id}.

    Como no Trabalho 2, so filme, cliente e prazo podem mudar. A data da locacao
    nao muda; por isso a comparacao da nova data prevista com ela e feita no
    service (Etapa 2), que conhece a locacao salva.
    """

    model_config = ConfigDict(extra='forbid')

    filme_id: int = Field(gt=0)
    cliente_nome: NomeCliente
    data_devolucao_prevista: date


class LocacaoDevolucaoRequest(BaseModel):
    """Corpo de POST /locacoes/{id}/devolucao.

    Sem data, a devolucao e registrada com a data de hoje. A comparacao com a
    data da locacao e feita no service (Etapa 2).
    """

    model_config = ConfigDict(extra='forbid')

    data_devolucao_real: Optional[date] = None


class LocacaoResponse(BaseModel):
    """Resposta da API. status e atrasada sao calculados, nunca recebidos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filme_id: int
    cliente_nome: str
    data_locacao: date
    data_devolucao_prevista: Optional[date] = None
    data_devolucao_real: Optional[date] = None
    status: Literal['Em aberto', 'Devolvido']
    atrasada: bool

    @model_validator(mode='after')
    def _datas_em_ordem(self):
        _validar_ordem_das_datas(
            self.data_locacao,
            self.data_devolucao_prevista,
            self.data_devolucao_real,
        )
        return self