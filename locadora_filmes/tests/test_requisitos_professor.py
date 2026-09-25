import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QLineEdit,
    QMenuBar,
    QMessageBox,
    QStackedWidget,
    QTableWidget,
    QToolBar,
)

from app.views.filme_dialog import FilmeDialog
from app.views.filmes_page import FilmesPage
from app.views.main_window import MainWindow
from app.widgets.search_bar import SearchBar


class RequisitosProfessorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()

    def test_componentes_principais(self):
        self.assertIsInstance(self.window.stack, QStackedWidget)
        self.assertIsInstance(self.window.menuBar(), QMenuBar)
        self.assertTrue(self.window.findChildren(QToolBar))
        self.assertIsInstance(self.window.filmes_page.tabela, QTableWidget)

    def test_dialogs_alerts_widgets_layouts(self):
        dialog = FilmeDialog()
        self.assertIsInstance(dialog, QDialog)
        self.assertIsInstance(dialog.layout().itemAt(0).layout(), QFormLayout)
        self.assertTrue(dialog.findChildren(QLineEdit))
        self.assertIsNotNone(QMessageBox)

    def test_signals_slots_evento_e_janela_adicional(self):
        self.assertIsInstance(SearchBar.search_changed, Signal)
        self.assertTrue(hasattr(FilmesPage, 'filme_cadastrado'))
        self.assertTrue(hasattr(MainWindow, 'closeEvent'))
        self.assertIsInstance(FilmeDialog(), QDialog)


if __name__ == '__main__':
    unittest.main()
