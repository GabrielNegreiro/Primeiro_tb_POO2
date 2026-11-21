from contextlib import contextmanager
from datetime import date
from typing import Callable, Optional

from ..models.filme import Filme
from ..models.locacao import Locacao
from ..repositories.locacoes import LocacaoIntegrityConflict, LocacaoRepository
from ..schemas.locacoes import (
    FiltroLocacao,
    LocacaoCreate,
    LocacaoDevolucaoRequest,
    LocacaoUpdate,
)
from .filmes import FilmeService


class LocacaoNotFoundError(LookupError):
    """Indica que a locacao ou o filme solicitado nao existe."""


class LocacaoConflictError(RuntimeError):
    """Indica que o estado atual impede a operacao (HTTP 409)."""


class LocacaoValidationError(ValueError):
    """Indica dado invalido que depende da locacao salva (HTTP 422)."""


class LocacaoService:
    """Centraliza as regras de negocio de locacoes.

    Toda operacao que altera locacao e disponibilidade do filme acontece na
    mesma transacao: o `FilmeService` recebido deve usar `auto_commit=False`,
    e somente este service confirma (se `auto_commit=True`) ou desfaz.
    """

    def __init__(
        self,
        repository: LocacaoRepository,
        filme_service: FilmeService,
        *,
        auto_commit: bool = False,
        hoje: Callable[[], date] = date.today,
    ):
        """Configura repository, servico de filmes e controle da transacao."""
        self.repository = repository
        self.filme_service = filme_service
        self.auto_commit = auto_commit
        self.hoje = hoje

    def criar(self, dados: LocacaoCreate) -> Locacao:
        """Registra uma locacao e torna o filme indisponivel (atomico)."""
        with self._transacao():
            filme = self._bloquear_filmes([dados.filme_id])[dados.filme_id]
            if not filme.disponivel:
                raise LocacaoConflictError('Filme indisponivel para locacao.')
            if self.repository.buscar_aberta_por_filme(dados.filme_id) is not None:
                raise LocacaoConflictError('O filme ja possui locacao em aberto.')
            locacao = self._persistir(self.repository.criar, dados.model_dump())
            self.filme_service.definir_disponibilidade(dados.filme_id, False)
            return locacao

    def listar(self, filtro: FiltroLocacao = FiltroLocacao.TODAS) -> list[Locacao]:
        """Lista locacoes conforme o filtro; atraso usa a data atual."""
        return self.repository.listar(filtro, self.hoje())

    def buscar_por_id(self, locacao_id: int) -> Locacao:
        """Retorna uma locacao ou informa que o recurso nao existe."""
        locacao = self.repository.buscar_por_id(locacao_id)
        if locacao is None:
            raise LocacaoNotFoundError('Locacao nao encontrada.')
        return locacao

    def atualizar(self, locacao_id: int, dados: LocacaoUpdate) -> Locacao:
        """Edita locacao em aberto; na troca de filme libera o anterior."""
        with self._transacao():
            locacao = self._buscar_bloqueada(locacao_id)
            if locacao.data_devolucao_real is not None:
                raise LocacaoConflictError(
                    'Somente locacoes em aberto podem ser editadas.'
                )
            if dados.data_devolucao_prevista < locacao.data_locacao:
                raise LocacaoValidationError(
                    'A data de devolucao prevista nao pode ser anterior '
                    'a data da locacao.'
                )

            filme_anterior = locacao.filme_id
            trocou = dados.filme_id != filme_anterior
            if trocou:
                filmes = self._bloquear_filmes([filme_anterior, dados.filme_id])
                novo = filmes[dados.filme_id]
                if not novo.disponivel or (
                    self.repository.buscar_aberta_por_filme(dados.filme_id)
                    is not None
                ):
                    raise LocacaoConflictError(
                        'Filme indisponivel para locacao.'
                    )

            locacao = self._persistir(
                self.repository.atualizar,
                locacao,
                dados.model_dump(),
            )
            if trocou:
                self.filme_service.definir_disponibilidade(filme_anterior, True)
                self.filme_service.definir_disponibilidade(dados.filme_id, False)
            return locacao

    def devolver(
        self,
        locacao_id: int,
        dados: Optional[LocacaoDevolucaoRequest] = None,
    ) -> Locacao:
        """Registra a devolucao e libera o filme se nao houver outra aberta."""
        with self._transacao():
            locacao = self._buscar_bloqueada(locacao_id)
            if locacao.data_devolucao_real is not None:
                raise LocacaoConflictError('Locacao ja devolvida.')

            data = (dados.data_devolucao_real if dados else None) or self.hoje()
            if data < locacao.data_locacao:
                raise LocacaoValidationError(
                    'A data de devolucao real nao pode ser anterior '
                    'a data da locacao.'
                )

            self._bloquear_filmes([locacao.filme_id])
            locacao = self._persistir(
                self.repository.registrar_devolucao,
                locacao,
                data,
            )
            if self.repository.buscar_aberta_por_filme(locacao.filme_id) is None:
                self.filme_service.definir_disponibilidade(locacao.filme_id, True)
            return locacao

    def excluir(self, locacao_id: int) -> None:
        """Exclui somente locacao ja devolvida; nunca remove o filme."""
        with self._transacao():
            locacao = self._buscar_bloqueada(locacao_id)
            if locacao.data_devolucao_real is None:
                raise LocacaoConflictError(
                    'Nao e possivel excluir uma locacao em aberto.'
                )
            self.repository.excluir(locacao)

    def _buscar_bloqueada(self, locacao_id: int) -> Locacao:
        """Busca a locacao com FOR UPDATE ou informa que nao existe."""
        locacao = self.repository.buscar_por_id(locacao_id, bloquear=True)
        if locacao is None:
            raise LocacaoNotFoundError('Locacao nao encontrada.')
        return locacao

    def _bloquear_filmes(self, filme_ids: list[int]) -> dict[int, Filme]:
        """Bloqueia os filmes (ordem crescente de id) e exige que existam."""
        filmes = self.repository.bloquear_filmes(filme_ids)
        if any(filme_id not in filmes for filme_id in filme_ids):
            raise LocacaoNotFoundError('Filme nao encontrado.')
        return filmes

    @staticmethod
    def _persistir(operacao, *argumentos):
        """Executa escrita do repository convertendo violacao de integridade."""
        try:
            return operacao(*argumentos)
        except LocacaoIntegrityConflict:
            raise LocacaoConflictError(
                'Conflito de integridade: o filme ja possui locacao em aberto.'
            ) from None

    @contextmanager
    def _transacao(self):
        """Confirma ao final (se auto_commit) ou desfaz tudo em qualquer erro."""
        try:
            yield
            if self.auto_commit:
                self.repository.confirmar()
        except Exception:
            self.repository.desfazer()
            raise