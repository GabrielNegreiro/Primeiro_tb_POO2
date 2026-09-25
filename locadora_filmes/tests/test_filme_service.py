import unittest

from app.models.filme import Filme
from app.services.filme_service import FilmeService


class FilmeServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = FilmeService([
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Drama Teste', 'Drama', 2020, 100, False),
        ])

    def test_listar_filmes(self):
        self.assertEqual(len(self.service.listar_filmes()), 2)

    def test_buscar_filmes(self):
        resultado = self.service.buscar_filmes('matrix')
        self.assertEqual(resultado[0].titulo, 'Matrix')

    def test_adicionar_filme(self):
        filme = self.service.adicionar_filme('Novo', 'Acao', 2024, 90)
        self.assertEqual(filme.id, 3)
        self.assertIn(filme, self.service.listar_filmes())

    def test_atualizar_filme(self):
        filme = self.service.atualizar_filme(1, 'Matrix Reloaded', 'Ficcao', 2003, 138, True)
        self.assertEqual(filme.titulo, 'Matrix Reloaded')

    def test_remover_filme(self):
        removido = self.service.remover_filme(1)
        self.assertEqual(removido.titulo, 'Matrix')
        self.assertIsNone(self.service.obter_filme(1))

    def test_listar_disponiveis(self):
        disponiveis = self.service.listar_disponiveis()
        self.assertEqual(len(disponiveis), 1)
        self.assertTrue(disponiveis[0].disponivel)


if __name__ == '__main__':
    unittest.main()
