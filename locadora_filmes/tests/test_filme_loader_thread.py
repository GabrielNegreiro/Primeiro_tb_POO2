import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from app.data.filme_repository import FilmeRepository
from app.models.filme import Filme
from app.workers.filme_loader_thread import FilmeLoaderThread


class FilmeLoaderThreadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_arquivo = (
            Path(self.diretorio_temporario.name) / 'filmes.json'
        )

    def tearDown(self):
        self.diretorio_temporario.cleanup()

    def _executar_thread(self, thread):
        thread.start()
        self.assertTrue(thread.wait(3000), 'A thread nao terminou no tempo esperado.')
        self.app.processEvents()

    def test_carrega_filmes_e_emite_signal_de_sucesso(self):
        repository = FilmeRepository(self.caminho_arquivo)
        esperados = [
            Filme(1, 'Interestelar', 'Ficcao', 2014, 169, True),
            Filme(2, 'Cidade de Deus', 'Drama', 2002, 130, False),
        ]
        repository.salvar_filmes(esperados)
        thread = FilmeLoaderThread(repository)
        sucesso_spy = QSignalSpy(thread.carregado)
        erro_spy = QSignalSpy(thread.erro)

        self._executar_thread(thread)

        self.assertEqual(sucesso_spy.count(), 1)
        self.assertEqual(erro_spy.count(), 0)
        carregados = sucesso_spy.at(0)[0]
        self.assertTrue(all(isinstance(filme, Filme) for filme in carregados))
        self.assertEqual(carregados, esperados)

    def test_arquivo_inexistente_emite_lista_vazia(self):
        repository = FilmeRepository(self.caminho_arquivo)
        thread = FilmeLoaderThread(repository)
        sucesso_spy = QSignalSpy(thread.carregado)
        erro_spy = QSignalSpy(thread.erro)

        self._executar_thread(thread)

        self.assertEqual(sucesso_spy.count(), 1)
        self.assertEqual(sucesso_spy.at(0)[0], [])
        self.assertEqual(erro_spy.count(), 0)

    def test_excecao_emite_signal_de_erro(self):
        repository = Mock(spec=FilmeRepository)
        repository.carregar_filmes.side_effect = RuntimeError('erro de teste')
        thread = FilmeLoaderThread(repository)
        sucesso_spy = QSignalSpy(thread.carregado)
        erro_spy = QSignalSpy(thread.erro)

        self._executar_thread(thread)

        self.assertEqual(sucesso_spy.count(), 0)
        self.assertEqual(erro_spy.count(), 1)
        self.assertIn('erro de teste', erro_spy.at(0)[0])


if __name__ == '__main__':
    unittest.main()
