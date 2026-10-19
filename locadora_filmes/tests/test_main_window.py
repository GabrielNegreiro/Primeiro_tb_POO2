import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenuBar, QStackedWidget, QToolBar

from app.data.filme_repository import FilmeRepository
from app.models.filme import Filme
from app.views.dashboard_page import DashboardPage
from app.views.filmes_page import FilmesPage
from app.views.locacoes_page import LocacoesPage
from app.views.main_window import MainWindow


class FilmeLoaderThreadFake(QObject):
    carregado = Signal(object)
    erro = Signal(str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.iniciada = False

    def start(self):
        self.iniciada = True
        try:
            filmes = self.repository.carregar_filmes()
        except Exception as excecao:
            self.erro.emit(str(excecao))
            return
        self.carregado.emit(filmes)

    def isRunning(self):
        return False

    def wait(self, _tempo=0):
        return True


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.filmes_persistidos = [
            Filme(3, 'Interestelar', 'Ficcao', 2014, 169, True),
            Filme(7, 'Cidade de Deus', 'Drama', 2002, 130, False),
        ]
        self.repository = Mock(spec=FilmeRepository)
        self.repository.carregar_filmes.return_value = self.filmes_persistidos

        self.repository_patch = patch(
            'app.views.main_window.FilmeRepository',
            return_value=self.repository,
        )
        self.loader_patch = patch(
            'app.views.main_window.FilmeLoaderThread',
            FilmeLoaderThreadFake,
        )
        self.repository_class = self.repository_patch.start()
        self.loader_patch.start()
        self.addCleanup(self.repository_patch.stop)
        self.addCleanup(self.loader_patch.stop)

        self.window = MainWindow()

    def test_paginas_e_stack(self):
        self.assertIsInstance(self.window.stack, QStackedWidget)
        self.assertIsInstance(self.window.dashboard_page, DashboardPage)
        self.assertIsInstance(self.window.filmes_page, FilmesPage)
        self.assertIsInstance(self.window.locacoes_page, LocacoesPage)

    def test_cria_repository_service_unico_e_loader(self):
        self.repository_class.assert_called_once_with()
        self.assertIs(self.window.filme_service.repository, self.repository)
        self.assertIs(
            self.window.filmes_page.filme_service,
            self.window.filme_service,
        )
        self.assertIs(
            self.window.dashboard_page.filme_service,
            self.window.filme_service,
        )
        self.assertIs(
            self.window.locacoes_page.filme_service,
            self.window.filme_service,
        )
        self.assertIs(
            self.window.locacao_service.filme_service,
            self.window.filme_service,
        )
        self.assertIsInstance(
            self.window.filme_loader_thread,
            FilmeLoaderThreadFake,
        )
        self.assertTrue(self.window.filme_loader_thread.iniciada)

    def test_repository_e_carregado_uma_unica_vez(self):
        self.repository.carregar_filmes.assert_called_once_with()
        self.assertEqual(
            self.window.filme_service.listar_filmes(),
            self.filmes_persistidos,
        )

    def test_signal_de_sucesso_atualiza_service_e_paginas(self):
        novos_filmes = [
            Filme(10, 'Novo Acervo', 'Drama', 2026, 100, True),
        ]

        self.window.filme_loader_thread.carregado.emit(novos_filmes)

        self.assertEqual(
            self.window.filme_service.listar_filmes(),
            novos_filmes,
        )
        self.assertEqual(self.window.filmes_page.tabela.rowCount(), 1)
        self.assertEqual(
            self.window.filmes_page.tabela.item(0, 1).text(),
            'Novo Acervo',
        )
        self.assertEqual(self.window.dashboard_page.label_disponiveis.text(), '1')

    def test_signal_de_erro_exibe_aviso(self):
        with patch('app.views.main_window.QMessageBox.warning') as warning:
            self.window.filme_loader_thread.erro.emit('arquivo corrompido')

        warning.assert_called_once()
        self.assertIn('arquivo corrompido', warning.call_args.args[2])
        self.assertEqual(
            self.window.statusBar().currentMessage(),
            'Falha ao carregar o acervo.',
        )

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
        self.assertEqual(
            self.window.filmes_page.tabela.rowCount(),
            len(self.filmes_persistidos),
        )


if __name__ == '__main__':
    unittest.main()
