from datetime import date
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.filme import Filme
from ..models.locacao import Locacao
from ..schemas.locacoes import FiltroLocacao


class LocacaoIntegrityConflict(RuntimeError):
    """Indica que uma restricao relacional impediu a operacao de locacao."""


class LocacaoRepository:
    """Concentra as operacoes SQLAlchemy sobre a tabela de locacoes.

    Nenhum metodo confirma a transacao, exceto `confirmar`: quem coordena a
    unidade de trabalho (locacao + disponibilidade do filme) e o service.
    """

    def __init__(self, session: Session):
        """Inicializa o repository com a sessao da unidade de trabalho."""
        self.session = session

    def criar(self, dados: dict) -> Locacao:
        """Insere uma locacao e obtem o identificador gerado pelo banco."""
        locacao = Locacao(**dados)
        self.session.add(locacao)
        self._sincronizar()
        return locacao

    def buscar_por_id(
        self,
        locacao_id: int,
        *,
        bloquear: bool = False,
    ) -> Optional[Locacao]:
        """Busca uma locacao; com `bloquear`, usa SELECT ... FOR UPDATE."""
        statement: Select = select(Locacao).where(Locacao.id == locacao_id)
        if bloquear:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self.session.scalars(statement).first()

    def listar(
        self,
        filtro: FiltroLocacao = FiltroLocacao.TODAS,
        hoje: Optional[date] = None,
    ) -> list[Locacao]:
        """Lista locacoes conforme o filtro (todas, ativas ou atrasadas)."""
        if filtro == FiltroLocacao.ATIVAS:
            return self.listar_ativas()
        if filtro == FiltroLocacao.ATRASADAS:
            return self.listar_atrasadas(hoje or date.today())
        return self.listar_todas()

    def listar_todas(self) -> list[Locacao]:
        """Retorna todas as locacoes, em ordem de identificador."""
        return self._executar(select(Locacao))

    def listar_ativas(self) -> list[Locacao]:
        """Retorna locacoes sem data de devolucao real."""
        return self._executar(
            select(Locacao).where(Locacao.data_devolucao_real.is_(None))
        )

    def listar_atrasadas(self, hoje: date) -> list[Locacao]:
        """Retorna locacoes abertas cujo prazo previsto e anterior a `hoje`."""
        return self._executar(
            select(Locacao).where(
                Locacao.data_devolucao_real.is_(None),
                Locacao.data_devolucao_prevista < hoje,
            )
        )

    def buscar_aberta_por_filme(self, filme_id: int) -> Optional[Locacao]:
        """Retorna a locacao em aberto do filme, se existir."""
        statement = select(Locacao).where(
            Locacao.filme_id == filme_id,
            Locacao.data_devolucao_real.is_(None),
        )
        return self.session.scalars(statement).first()

    def atualizar(self, locacao: Locacao, dados: dict) -> Locacao:
        """Aplica campos validados e sincroniza a alteracao na transacao."""
        for campo, valor in dados.items():
            setattr(locacao, campo, valor)
        self._sincronizar()
        return locacao

    def registrar_devolucao(self, locacao: Locacao, data: date) -> Locacao:
        """Grava a data efetiva de devolucao."""
        locacao.data_devolucao_real = data
        self._sincronizar()
        return locacao

    def excluir(self, locacao: Locacao) -> None:
        """Remove a locacao; a regra de so excluir devolvidas e do service."""
        self.session.delete(locacao)
        self._sincronizar()

    def bloquear_filmes(self, filme_ids: list[int]) -> dict[int, Filme]:
        """Bloqueia filmes com FOR UPDATE, sempre em ordem crescente de id.

        A ordem fixa evita deadlock quando duas requisicoes disputam os mesmos
        filmes (por exemplo, em trocas de filme). Retorna somente os que existem.
        """
        ids = sorted(set(filme_ids))
        statement = (
            select(Filme)
            .where(Filme.id.in_(ids))
            .order_by(Filme.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return {filme.id: filme for filme in self.session.scalars(statement)}

    def confirmar(self) -> None:
        """Confirma explicitamente a unidade de trabalho atual."""
        self.session.commit()

    def desfazer(self) -> None:
        """Desfaz a unidade de trabalho atual e libera os bloqueios."""
        self.session.rollback()

    def _executar(self, statement: Select) -> list[Locacao]:
        """Executa a consulta ordenando por identificador."""
        return list(self.session.scalars(statement.order_by(Locacao.id)).all())

    def _sincronizar(self) -> None:
        """Envia as alteracoes ao banco, traduzindo violacoes de integridade."""
        try:
            self.session.flush()
        except IntegrityError as error:
            raise LocacaoIntegrityConflict from error