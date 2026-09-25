import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QPushButton

from app.models.filme import Filme
from app.services.filme_service import FilmeService
from app.views.filmes_page import FilmesPage
from app.widgets.search_bar import SearchBar


class FilmesPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.service = FilmeService([
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Toy Story', 'Animacao', 1995, 81, True),
        ])
        self.page = FilmesPage(self.service)

    def test_instanciacao_e_tabela(self):
        self.assertEqual(self.page.tabela.rowCount(), 2)
        self.assertIsInstance(self.page.search_bar, SearchBar)

    def test_pesquisa(self):
        self.page.pesquisar('toy')
        self.assertEqual(self.page.tabela.rowCount(), 1)
        self.assertEqual(self.page.tabela.item(0, 1).text(), 'Toy Story')

    def test_botoes_existem(self):
        botoes = self.page.findChildren(QPushButton)
        textos = {botao.text() for botao in botoes}
        self.assertIn('Novo Filme', textos)
        self.assertIn('Editar', textos)
        self.assertIn('Excluir', textos)

    def test_signal_personalizado(self):
        chamadas = []
        self.page.filme_cadastrado.connect(lambda: chamadas.append(True))
        self.page.filme_cadastrado.emit()
        self.assertEqual(chamadas, [True])

    def test_selecao_de_filme(self):
        self.page.tabela.selectRow(0)
        filme = self.page.filme_selecionado()
        self.assertEqual(filme.titulo, 'Matrix')


if __name__ == '__main__':
    unittest.main()
