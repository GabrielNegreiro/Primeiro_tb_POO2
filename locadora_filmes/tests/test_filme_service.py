import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.data.filme_repository import FilmeRepository
from app.models.filme import Filme
from app.services.filme_service import FilmeService


class FilmeServiceTest(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_arquivo = (
            Path(self.diretorio_temporario.name) / 'filmes.json'
        )
        self.repository = FilmeRepository(self.caminho_arquivo)
        self.filmes_iniciais = [
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Drama Teste', 'Drama', 2020, 100, False),
            Filme(5, 'Toy Story', 'Animacao', 1995, 81, True),
        ]
        self.repository.salvar_filmes(self.filmes_iniciais)
        self.service = FilmeService(self.repository)

    def tearDown(self):
        self.diretorio_temporario.cleanup()

    def test_carrega_filmes_existentes_do_repository(self):
        self.assertEqual(self.service.listar_filmes(), self.filmes_iniciais)

    def test_buscar_filmes(self):
        resultado = self.service.buscar_filmes('matrix')
        self.assertEqual(resultado[0].titulo, 'Matrix')

    def test_adicionar_filme_salva_no_json(self):
        filme = self.service.adicionar_filme('Novo', 'Acao', 2024, 90)

        persistidos = self.repository.carregar_filmes()
        self.assertEqual(filme.id, 6)
        self.assertIn(filme, persistidos)

    def test_atualizar_filme_salva_no_json(self):
        filme = self.service.atualizar_filme(
            1, 'Matrix Reloaded', 'Ficcao', 2003, 138, True
        )

        persistido = next(
            item for item in self.repository.carregar_filmes() if item.id == 1
        )
        self.assertEqual(filme.titulo, 'Matrix Reloaded')
        self.assertEqual(persistido.titulo, 'Matrix Reloaded')
        self.assertEqual(persistido.ano, 2003)

    def test_remover_filme_remove_do_json(self):
        removido = self.service.remover_filme(1)

        ids_persistidos = [
            filme.id for filme in self.repository.carregar_filmes()
        ]
        self.assertEqual(removido.titulo, 'Matrix')
        self.assertNotIn(1, ids_persistidos)

    def test_buscar_por_id_encontra_filme(self):
        filme = self.service.buscar_por_id(5)

        self.assertIsNotNone(filme)
        self.assertEqual(filme.titulo, 'Toy Story')

    def test_buscar_por_id_retorna_none_para_id_inexistente(self):
        self.assertIsNone(self.service.buscar_por_id(999))

    def test_definir_disponibilidade_atualiza_e_persiste(self):
        filme = self.service.definir_disponibilidade(1, False)

        persistido = next(
            item for item in self.repository.carregar_filmes() if item.id == 1
        )
        self.assertFalse(filme.disponivel)
        self.assertFalse(persistido.disponivel)

    def test_definir_disponibilidade_igual_nao_regrava(self):
        repository = Mock(spec=FilmeRepository)
        service = FilmeService(
            repository,
            filmes=[Filme(1, 'Matrix', 'Ficcao', 1999, 136, True)],
        )

        service.definir_disponibilidade(1, True)

        repository.salvar_filmes.assert_not_called()

    def test_geracao_de_id_usa_maior_id_existente(self):
        novo = self.service.adicionar_filme('Filme 6', 'Drama', 2025, 110)

        self.assertEqual(novo.id, 6)
        self.assertEqual(
            len({filme.id for filme in self.service.listar_filmes()}),
            len(self.service.listar_filmes()),
        )

    def test_novo_service_recupera_alteracoes_persistidas(self):
        adicionado = self.service.adicionar_filme(
            'Persistente', 'Documentario', 2026, 80
        )

        novo_service = FilmeService(self.repository)

        self.assertEqual(
            novo_service.buscar_por_id(adicionado.id).titulo,
            'Persistente',
        )

    def test_listar_disponiveis(self):
        disponiveis = self.service.listar_disponiveis()

        self.assertEqual(len(disponiveis), 2)
        self.assertTrue(all(filme.disponivel for filme in disponiveis))

    def test_repository_vazio_usa_dados_iniciais_sem_duplicar(self):
        repository_vazio = FilmeRepository(
            Path(self.diretorio_temporario.name) / 'vazio.json'
        )
        service = FilmeService(repository_vazio)

        self.assertEqual(len(service.listar_filmes()), 4)
        service.adicionar_filme('Quinto Filme', 'Drama', 2026, 100)

        reiniciado = FilmeService(repository_vazio)
        self.assertEqual(len(reiniciado.listar_filmes()), 5)
        self.assertEqual(len({filme.id for filme in reiniciado.listar_filmes()}), 5)

    def test_carregamento_automatico_desativado_nao_le_repository(self):
        repository = Mock(spec=FilmeRepository)

        service = FilmeService(repository, carregar_ao_iniciar=False)

        repository.carregar_filmes.assert_not_called()
        self.assertEqual(service.listar_filmes(), [])

    def test_aplicar_filmes_carregados_atualiza_acervo_e_proximo_id(self):
        repository = Mock(spec=FilmeRepository)
        service = FilmeService(repository, carregar_ao_iniciar=False)
        carregados = [
            Filme(2, 'Filme 2', 'Drama', 2020, 90, True),
            Filme(8, 'Filme 8', 'Acao', 2024, 120, True),
        ]

        service.aplicar_filmes_carregados(carregados)
        novo = service.adicionar_filme('Filme 9', 'Comedia', 2026, 100)

        self.assertIs(service.buscar_por_id(8), carregados[1])
        self.assertEqual(novo.id, 9)
        repository.salvar_filmes.assert_called_once()

    def test_aplicar_lista_vazia_usa_fallback_sem_persistir(self):
        repository = Mock(spec=FilmeRepository)
        service = FilmeService(repository, carregar_ao_iniciar=False)

        service.aplicar_filmes_carregados([])

        self.assertEqual(len(service.listar_filmes()), 4)
        repository.salvar_filmes.assert_not_called()


if __name__ == '__main__':
    unittest.main()
