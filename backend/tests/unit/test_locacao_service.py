import unittest
from datetime import date
from unittest.mock import Mock

from backend.app.models.filme import Filme
from backend.app.models.locacao import Locacao
from backend.app.repositories.locacoes import (
    LocacaoIntegrityConflict,
    LocacaoRepository,
)
from backend.app.schemas.locacoes import (
    FiltroLocacao,
    LocacaoCreate,
    LocacaoDevolucaoRequest,
    LocacaoUpdate,
)
from backend.app.services.filmes import FilmeService
from backend.app.services.locacoes import (
    LocacaoConflictError,
    LocacaoNotFoundError,
    LocacaoService,
    LocacaoValidationError,
)

HOJE = date(2026, 11, 20)


def novo_filme(filme_id=1, disponivel=True):
    return Filme(
        id=filme_id,
        titulo=f'Filme {filme_id}',
        genero='Teste',
        ano=2000,
        duracao=90,
        disponivel=disponivel,
    )


def nova_locacao(filme_id=1, real=None):
    return Locacao(
        id=10,
        filme_id=filme_id,
        cliente_nome='Ana',
        data_locacao=date(2026, 11, 10),
        data_devolucao_prevista=date(2026, 11, 17),
        data_devolucao_real=real,
    )


class LocacaoServiceTest(unittest.TestCase):
    def setUp(self):
        self.repository = Mock(spec=LocacaoRepository)
        self.filmes = Mock(spec=FilmeService)
        self.service = LocacaoService(
            self.repository,
            self.filmes,
            auto_commit=True,
            hoje=lambda: HOJE,
        )

    def dados_criacao(self, filme_id=1):
        return LocacaoCreate(
            filme_id=filme_id,
            cliente_nome='Ana',
            data_locacao=date(2026, 11, 20),
            data_devolucao_prevista=date(2026, 11, 27),
        )

    # --- cadastro ---------------------------------------------------------

    def test_cadastro_valido_torna_filme_indisponivel_e_confirma(self):
        locacao = nova_locacao()
        self.repository.bloquear_filmes.return_value = {1: novo_filme()}
        self.repository.buscar_aberta_por_filme.return_value = None
        self.repository.criar.return_value = locacao

        resultado = self.service.criar(self.dados_criacao())

        self.assertIs(resultado, locacao)
        self.filmes.definir_disponibilidade.assert_called_once_with(1, False)
        self.repository.confirmar.assert_called_once()
        self.repository.desfazer.assert_not_called()

    def test_cadastro_filme_inexistente(self):
        self.repository.bloquear_filmes.return_value = {}

        with self.assertRaises(LocacaoNotFoundError):
            self.service.criar(self.dados_criacao(99))

        self.repository.criar.assert_not_called()
        self.repository.desfazer.assert_called_once()

    def test_cadastro_filme_indisponivel(self):
        self.repository.bloquear_filmes.return_value = {
            1: novo_filme(disponivel=False)
        }

        with self.assertRaises(LocacaoConflictError):
            self.service.criar(self.dados_criacao())

        self.repository.criar.assert_not_called()
        self.repository.confirmar.assert_not_called()

    def test_cadastro_com_locacao_aberta_existente(self):
        self.repository.bloquear_filmes.return_value = {1: novo_filme()}
        self.repository.buscar_aberta_por_filme.return_value = nova_locacao()

        with self.assertRaises(LocacaoConflictError):
            self.service.criar(self.dados_criacao())

        self.repository.criar.assert_not_called()

    def test_cadastro_conflito_do_indice_unico_vira_409_com_rollback(self):
        self.repository.bloquear_filmes.return_value = {1: novo_filme()}
        self.repository.buscar_aberta_por_filme.return_value = None
        self.repository.criar.side_effect = LocacaoIntegrityConflict

        with self.assertRaises(LocacaoConflictError):
            self.service.criar(self.dados_criacao())

        self.repository.desfazer.assert_called_once()
        self.repository.confirmar.assert_not_called()

    def test_rollback_quando_atualizar_disponibilidade_falha(self):
        self.repository.bloquear_filmes.return_value = {1: novo_filme()}
        self.repository.buscar_aberta_por_filme.return_value = None
        self.repository.criar.return_value = nova_locacao()
        self.filmes.definir_disponibilidade.side_effect = RuntimeError('falha')

        with self.assertRaises(RuntimeError):
            self.service.criar(self.dados_criacao())

        self.repository.desfazer.assert_called_once()
        self.repository.confirmar.assert_not_called()

    def test_sem_auto_commit_service_nao_confirma(self):
        service = LocacaoService(self.repository, self.filmes, hoje=lambda: HOJE)
        self.repository.bloquear_filmes.return_value = {1: novo_filme()}
        self.repository.buscar_aberta_por_filme.return_value = None
        self.repository.criar.return_value = nova_locacao()

        service.criar(self.dados_criacao())

        self.repository.confirmar.assert_not_called()

    # --- consultas e listagens -------------------------------------------

    def test_consulta_por_id(self):
        locacao = nova_locacao()
        self.repository.buscar_por_id.return_value = locacao

        self.assertIs(self.service.buscar_por_id(10), locacao)

    def test_consulta_locacao_inexistente(self):
        self.repository.buscar_por_id.return_value = None

        with self.assertRaises(LocacaoNotFoundError):
            self.service.buscar_por_id(99)

    def test_listagens_delegam_filtro_e_data_atual(self):
        for filtro in FiltroLocacao:
            with self.subTest(filtro=filtro):
                self.repository.listar.return_value = []
                self.service.listar(filtro)
                self.repository.listar.assert_called_with(filtro, HOJE)

    # --- edicao -----------------------------------------------------------

    def dados_edicao(self, filme_id=1, prevista=date(2026, 11, 30)):
        return LocacaoUpdate(
            filme_id=filme_id,
            cliente_nome='Bia',
            data_devolucao_prevista=prevista,
        )

    def test_edicao_valida_sem_trocar_filme(self):
        locacao = nova_locacao()
        self.repository.buscar_por_id.return_value = locacao
        self.repository.atualizar.return_value = locacao

        self.service.atualizar(10, self.dados_edicao())

        self.repository.bloquear_filmes.assert_not_called()
        self.filmes.definir_disponibilidade.assert_not_called()
        self.repository.confirmar.assert_called_once()

    def test_edicao_de_locacao_devolvida(self):
        self.repository.buscar_por_id.return_value = nova_locacao(
            real=date(2026, 11, 15)
        )

        with self.assertRaises(LocacaoConflictError):
            self.service.atualizar(10, self.dados_edicao())

        self.repository.atualizar.assert_not_called()

    def test_edicao_com_prazo_anterior_a_locacao(self):
        self.repository.buscar_por_id.return_value = nova_locacao()

        with self.assertRaises(LocacaoValidationError):
            self.service.atualizar(10, self.dados_edicao(prevista=date(2026, 11, 1)))

    def test_edicao_de_locacao_inexistente(self):
        self.repository.buscar_por_id.return_value = None

        with self.assertRaises(LocacaoNotFoundError):
            self.service.atualizar(99, self.dados_edicao())

    def test_troca_de_filme_libera_anterior_e_bloqueia_novo(self):
        locacao = nova_locacao(filme_id=1)
        self.repository.buscar_por_id.return_value = locacao
        self.repository.bloquear_filmes.return_value = {
            1: novo_filme(1, False),
            2: novo_filme(2, True),
        }
        self.repository.buscar_aberta_por_filme.return_value = None
        self.repository.atualizar.return_value = locacao

        self.service.atualizar(10, self.dados_edicao(filme_id=2))

        self.repository.bloquear_filmes.assert_called_once_with([1, 2])
        self.filmes.definir_disponibilidade.assert_any_call(1, True)
        self.filmes.definir_disponibilidade.assert_any_call(2, False)
        self.assertEqual(self.filmes.definir_disponibilidade.call_count, 2)

    def test_troca_para_filme_indisponivel(self):
        self.repository.buscar_por_id.return_value = nova_locacao(filme_id=1)
        self.repository.bloquear_filmes.return_value = {
            1: novo_filme(1, False),
            2: novo_filme(2, False),
        }

        with self.assertRaises(LocacaoConflictError):
            self.service.atualizar(10, self.dados_edicao(filme_id=2))

        self.repository.atualizar.assert_not_called()
        self.filmes.definir_disponibilidade.assert_not_called()

    def test_troca_para_filme_inexistente(self):
        self.repository.buscar_por_id.return_value = nova_locacao(filme_id=1)
        self.repository.bloquear_filmes.return_value = {1: novo_filme(1, False)}

        with self.assertRaises(LocacaoNotFoundError):
            self.service.atualizar(10, self.dados_edicao(filme_id=2))

    # --- devolucao --------------------------------------------------------

    def test_devolucao_valida_usa_data_de_hoje_e_libera_filme(self):
        locacao = nova_locacao()
        self.repository.buscar_por_id.return_value = locacao
        self.repository.bloquear_filmes.return_value = {1: novo_filme(1, False)}
        self.repository.registrar_devolucao.return_value = locacao
        self.repository.buscar_aberta_por_filme.return_value = None

        self.service.devolver(10)

        self.repository.registrar_devolucao.assert_called_once_with(locacao, HOJE)
        self.filmes.definir_disponibilidade.assert_called_once_with(1, True)
        self.repository.confirmar.assert_called_once()

    def test_devolucao_com_data_informada(self):
        locacao = nova_locacao()
        self.repository.buscar_por_id.return_value = locacao
        self.repository.bloquear_filmes.return_value = {1: novo_filme(1, False)}
        self.repository.registrar_devolucao.return_value = locacao
        self.repository.buscar_aberta_por_filme.return_value = None

        self.service.devolver(
            10, LocacaoDevolucaoRequest(data_devolucao_real=date(2026, 11, 18))
        )

        self.repository.registrar_devolucao.assert_called_once_with(
            locacao, date(2026, 11, 18)
        )

    def test_devolucao_nao_libera_filme_com_outra_locacao_aberta(self):
        locacao = nova_locacao()
        self.repository.buscar_por_id.return_value = locacao
        self.repository.bloquear_filmes.return_value = {1: novo_filme(1, False)}
        self.repository.registrar_devolucao.return_value = locacao
        self.repository.buscar_aberta_por_filme.return_value = nova_locacao()

        self.service.devolver(10)

        self.filmes.definir_disponibilidade.assert_not_called()

    def test_devolucao_repetida(self):
        self.repository.buscar_por_id.return_value = nova_locacao(
            real=date(2026, 11, 15)
        )

        with self.assertRaises(LocacaoConflictError):
            self.service.devolver(10)

        self.repository.registrar_devolucao.assert_not_called()

    def test_devolucao_com_data_anterior_a_locacao(self):
        self.repository.buscar_por_id.return_value = nova_locacao()

        with self.assertRaises(LocacaoValidationError):
            self.service.devolver(
                10, LocacaoDevolucaoRequest(data_devolucao_real=date(2026, 11, 1))
            )

        self.repository.registrar_devolucao.assert_not_called()

    def test_devolucao_de_locacao_inexistente(self):
        self.repository.buscar_por_id.return_value = None

        with self.assertRaises(LocacaoNotFoundError):
            self.service.devolver(99)

    # --- exclusao ---------------------------------------------------------

    def test_exclusao_de_locacao_devolvida(self):
        locacao = nova_locacao(real=date(2026, 11, 15))
        self.repository.buscar_por_id.return_value = locacao

        self.service.excluir(10)

        self.repository.excluir.assert_called_once_with(locacao)
        self.repository.confirmar.assert_called_once()

    def test_exclusao_de_locacao_aberta(self):
        self.repository.buscar_por_id.return_value = nova_locacao()

        with self.assertRaises(LocacaoConflictError):
            self.service.excluir(10)

        self.repository.excluir.assert_not_called()
        self.repository.desfazer.assert_called_once()

    def test_exclusao_de_locacao_inexistente(self):
        self.repository.buscar_por_id.return_value = None

        with self.assertRaises(LocacaoNotFoundError):
            self.service.excluir(99)


if __name__ == '__main__':
    unittest.main()