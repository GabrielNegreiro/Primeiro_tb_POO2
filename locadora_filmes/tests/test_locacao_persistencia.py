import tempfile
import unittest
from pathlib import Path

from app.data.filme_repository import FilmeRepository
from app.data.locacao_repository import LocacaoRepository
from app.models.filme import Filme
from app.services.filme_service import FilmeService
from app.services.locacao_service import LocacaoService


class LocacaoPersistenciaTest(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        diretorio = Path(self.diretorio_temporario.name)
        self.filme_repository = FilmeRepository(diretorio / 'filmes.json')
        self.locacao_repository = LocacaoRepository(diretorio / 'locacoes.csv')
        self.filme_repository.salvar_filmes([
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Toy Story', 'Animacao', 1995, 81, True),
        ])
        self.filme_service = FilmeService(self.filme_repository)
        self.locacao_service = LocacaoService(
            self.locacao_repository,
            self.filme_service,
        )

    def tearDown(self):
        self.diretorio_temporario.cleanup()

    def test_registrar_persiste_filme_indisponivel(self):
        filme = self.filme_service.buscar_por_id(1)

        self.locacao_service.criar_locacao(filme, 'Ana', 7)

        filmes_recarregados = self._recarregar_filmes()
        locacoes_recarregadas = self._recarregar_locacoes(filmes_recarregados)
        self.assertFalse(filme.disponivel)
        self.assertFalse(filmes_recarregados.buscar_por_id(1).disponivel)
        self.assertEqual(len(locacoes_recarregadas.listar_todas()), 1)
        self.assertEqual(locacoes_recarregadas.listar_todas()[0].filme.id, 1)

    def test_devolver_persiste_filme_disponivel(self):
        locacao = self.locacao_service.criar_locacao(
            self.filme_service.buscar_por_id(1), 'Ana', 7
        )

        self.locacao_service.devolver_locacao(locacao)

        filmes_recarregados = self._recarregar_filmes()
        locacoes_recarregadas = self._recarregar_locacoes(filmes_recarregados)
        self.assertTrue(locacao.filme.disponivel)
        self.assertTrue(filmes_recarregados.buscar_por_id(1).disponivel)
        self.assertIsNotNone(
            locacoes_recarregadas.listar_todas()[0].data_devolucao_real
        )

    def test_editar_troca_persiste_disponibilidade_dos_dois_filmes(self):
        filme_a = self.filme_service.buscar_por_id(1)
        filme_b = self.filme_service.buscar_por_id(2)
        locacao = self.locacao_service.criar_locacao(filme_a, 'Ana', 7)

        self.locacao_service.atualizar_locacao(locacao, filme_b, 'Bia', 10)

        recarregado = self._recarregar_filmes()
        locacoes_recarregadas = self._recarregar_locacoes(recarregado)
        self.assertTrue(filme_a.disponivel)
        self.assertFalse(filme_b.disponivel)
        self.assertTrue(recarregado.buscar_por_id(1).disponivel)
        self.assertFalse(recarregado.buscar_por_id(2).disponivel)
        self.assertEqual(locacoes_recarregadas.listar_todas()[0].filme.id, 2)
        self.assertEqual(locacoes_recarregadas.listar_todas()[0].cliente_nome, 'Bia')

    def test_reinicializacao_reconstroi_locacao_e_referencia_do_filme(self):
        self.locacao_service.criar_locacao(
            self.filme_service.buscar_por_id(1), 'Ana', 7
        )

        filmes_recarregados = self._recarregar_filmes()
        locacoes_recarregadas = LocacaoService(
            self.locacao_repository,
            filmes_recarregados,
        )
        locacoes_recarregadas.carregar(filmes_recarregados.buscar_por_id)

        locacao = locacoes_recarregadas.listar_todas()[0]
        filme = filmes_recarregados.buscar_por_id(1)
        self.assertIs(locacao.filme, filme)
        self.assertFalse(filme.disponivel)

    def test_carregamento_corrige_e_persiste_json_desatualizado(self):
        self.locacao_service.criar_locacao(
            self.filme_service.buscar_por_id(1), 'Ana', 7
        )
        filmes_desatualizados = self.filme_repository.carregar_filmes()
        filmes_desatualizados[0].disponivel = True
        self.filme_repository.salvar_filmes(filmes_desatualizados)

        filmes_recarregados = self._recarregar_filmes()
        locacoes_recarregadas = LocacaoService(
            self.locacao_repository,
            filmes_recarregados,
        )
        locacoes_recarregadas.carregar(filmes_recarregados.buscar_por_id)

        self.assertFalse(filmes_recarregados.buscar_por_id(1).disponivel)
        self.assertFalse(self._recarregar_filmes().buscar_por_id(1).disponivel)

    def test_excluir_locacao_devolvida_mantem_filme_disponivel(self):
        locacao = self.locacao_service.criar_locacao(
            self.filme_service.buscar_por_id(1), 'Ana', 7
        )
        self.locacao_service.devolver_locacao(locacao)

        self.locacao_service.excluir_locacao(locacao)

        filmes_recarregados = self._recarregar_filmes()
        locacoes_recarregadas = LocacaoService(
            self.locacao_repository,
            filmes_recarregados,
        )
        locacoes_recarregadas.carregar(filmes_recarregados.buscar_por_id)
        self.assertTrue(filmes_recarregados.buscar_por_id(1).disponivel)
        self.assertEqual(locacoes_recarregadas.listar_todas(), [])

    def _recarregar_filmes(self):
        return FilmeService(self.filme_repository)

    def _recarregar_locacoes(self, filme_service):
        locacao_service = LocacaoService(
            self.locacao_repository,
            filme_service,
        )
        locacao_service.carregar(filme_service.buscar_por_id)
        return locacao_service


if __name__ == '__main__':
    unittest.main()
