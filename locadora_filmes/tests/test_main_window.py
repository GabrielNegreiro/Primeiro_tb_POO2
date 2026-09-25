import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QMenuBar, QStackedWidget, QToolBar

from app.views.dashboard_page import DashboardPage
from app.views.filmes_page import FilmesPage
from app.views.locacoes_page import LocacoesPage
from app.views.main_window import MainWindow


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def test_paginas_e_stack(self):
        self.assertIsInstance(self.window.stack, QStackedWidget)
        self.assertIsInstance(self.window.dashboard_page, DashboardPage)
        self.assertIsInstance(self.window.filmes_page, FilmesPage)
        self.assertIsInstance(self.window.locacoes_page, LocacoesPage)

    def test_navegacao_funciona(self):
        self.window.ir_filmes()
        self.assertEqual(self.window.stack.currentWidget(), self.window.filmes_page)
        self.window.ir_locacoes()
        self.assertEqual(self.window.stack.currentWidget(), self.window.locacoes_page)

    def test_menu_toolbar_e_sobre(self):
        self.assertIsInstance(self.window.menuBar(), QMenuBar)
        self.assertTrue(self.window.findChildren(QToolBar))
        with patch('app.views.main_window.SobreDialog') as sobre_dialog:
            self.window.mostrar_sobre()
            sobre_dialog.assert_called_once_with(self.window)

    def test_integracao_atualizar_nao_lanca_excecao(self):
        self.window.atualizar_tudo()
        self.assertGreaterEqual(self.window.filmes_page.tabela.rowCount(), 1)


if __name__ == '__main__':
    unittest.main()
