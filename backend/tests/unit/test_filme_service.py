import unittest
from unittest.mock import Mock

from backend.app.models.filme import Filme
from backend.app.repositories.filmes import FilmeIntegrityConflict, FilmeRepository
from backend.app.services.filmes import (
    FilmeConflictError,
    FilmeNotFoundError,
    FilmeService,
)


class FilmeServiceTest(unittest.TestCase):
    def setUp(self):
        self.repository = Mock(spec=FilmeRepository)
        self.service = FilmeService(self.repository)

    def test_buscar_filme_inexistente(self):
        self.repository.buscar_por_id.return_value = None

        with self.assertRaises(FilmeNotFoundError):
            self.service.buscar_por_id(99)

    def test_definir_disponibilidade_reutiliza_repository(self):
        filme = Filme(
            id=1,
            titulo='Matrix',
            genero='Ficcao',
            ano=1999,
            duracao=136,
            disponivel=True,
        )
        self.repository.buscar_por_id.return_value = filme
        self.repository.atualizar.return_value = filme

        resultado = self.service.definir_disponibilidade(1, False)

        self.assertIs(resultado, filme)
        self.repository.atualizar.assert_called_once_with(
            filme,
            {'disponivel': False},
        )

    def test_excluir_indisponivel_gera_conflito(self):
        filme = Filme(
            id=1,
            titulo='Matrix',
            genero='Ficcao',
            ano=1999,
            duracao=136,
            disponivel=False,
        )
        self.repository.buscar_por_id.return_value = filme

        with self.assertRaises(FilmeConflictError):
            self.service.excluir(1)

        self.repository.excluir.assert_not_called()

    def test_excluir_com_locacao_gera_conflito(self):
        filme = Filme(
            id=1,
            titulo='Matrix',
            genero='Ficcao',
            ano=1999,
            duracao=136,
            disponivel=True,
        )
        self.repository.buscar_por_id.return_value = filme
        self.repository.excluir.side_effect = FilmeIntegrityConflict

        with self.assertRaisesRegex(FilmeConflictError, 'locacoes'):
            self.service.excluir(1)


if __name__ == '__main__':
    unittest.main()

