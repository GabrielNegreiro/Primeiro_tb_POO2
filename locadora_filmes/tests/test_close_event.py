import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QMessageBox

from app.views.main_window import MainWindow


class CloseEventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.windows = []
        self.loaders = []

    def tearDown(self):
        for loader in self.loaders:
            if loader.isRunning():
                self.assertTrue(loader.wait(5000))
        for window in self.windows:
            if window.locacoes_page.exportacao_em_andamento():
                self.assertTrue(window.locacoes_page.aguardar_exportacao(5000))
            window.deleteLater()
        self.app.processEvents()

    def criar_window(self):
        window = MainWindow()
        self.windows.append(window)
        self.loaders.append(window.filme_loader_thread)
        return window

    def test_close_event_yes_aceita(self):
        window = self.criar_window()
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window.closeEvent(evento)

        evento.accept.assert_called_once()
        evento.ignore.assert_not_called()

    def test_close_event_no_ignora(self):
        window = self.criar_window()
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.No,
        ):
            window.closeEvent(evento)

        evento.ignore.assert_called_once()
        evento.accept.assert_not_called()

    def test_cleanup_aguarda_carregamento_real_lento(self):
        with patch(
            'app.views.main_window.FilmeRepository.carregar_filmes',
            side_effect=lambda: (time.sleep(0.2), [])[1],
        ):
            window = self.criar_window()
            evento = Mock()
            self.assertTrue(window.filme_loader_thread.isRunning())

            with patch(
                'app.views.main_window.QMessageBox.question',
                return_value=QMessageBox.StandardButton.No,
            ):
                window.closeEvent(evento)

        evento.ignore.assert_called_once()
        evento.accept.assert_not_called()

    def test_close_event_aguarda_thread_em_execucao(self):
        window = self.criar_window()
        if window.filme_loader_thread.isRunning():
            window.filme_loader_thread.wait(3000)
        loader = Mock()
        loader.isRunning.return_value = True
        loader.wait.return_value = True
        window.filme_loader_thread = loader
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window.closeEvent(evento)

        loader.wait.assert_called_once_with(3000)
        evento.accept.assert_called_once()
        evento.ignore.assert_not_called()

    def test_close_event_mantem_aberta_se_thread_nao_terminar(self):
        window = self.criar_window()
        if window.filme_loader_thread.isRunning():
            window.filme_loader_thread.wait(3000)
        loader = Mock()
        loader.isRunning.return_value = True
        loader.wait.return_value = False
        window.filme_loader_thread = loader
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ), patch('app.views.main_window.QMessageBox.information') as information:
            window.closeEvent(evento)

        information.assert_called_once()
        evento.ignore.assert_called_once()
        evento.accept.assert_not_called()

    def test_close_event_aguarda_exportacao_em_execucao(self):
        window = self.criar_window()
        if window.filme_loader_thread.isRunning():
            window.filme_loader_thread.wait(3000)
        exportacao = Mock()
        exportacao.isRunning.return_value = True
        exportacao.wait.return_value = True
        window.locacoes_page.thread_exportacao = exportacao
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window.closeEvent(evento)

        exportacao.wait.assert_called_once_with(3000)
        evento.accept.assert_called_once()
        evento.ignore.assert_not_called()
        window.locacoes_page.thread_exportacao = None

    def test_close_event_mantem_aberta_se_exportacao_nao_terminar(self):
        window = self.criar_window()
        if window.filme_loader_thread.isRunning():
            window.filme_loader_thread.wait(3000)
        exportacao = Mock()
        exportacao.isRunning.return_value = True
        exportacao.wait.return_value = False
        window.locacoes_page.thread_exportacao = exportacao
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ), patch('app.views.main_window.QMessageBox.information') as information:
            window.closeEvent(evento)

        exportacao.wait.assert_called_once_with(3000)
        information.assert_called_once()
        evento.ignore.assert_called_once()
        evento.accept.assert_not_called()
        window.locacoes_page.thread_exportacao = None

    def test_close_event_aguarda_exportacao_real_lenta(self):
        window = self.criar_window()
        if window.filme_loader_thread.isRunning():
            window.filme_loader_thread.wait(3000)
        evento = Mock()

        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / 'relatorio.txt'
            with patch(
                'app.views.locacoes_page.QFileDialog.getSaveFileName',
                return_value=(str(caminho), 'Arquivo de texto (*.txt)'),
            ), patch(
                'app.views.exportar_thread.RelatorioService.exportar_txt',
                side_effect=lambda *_args: time.sleep(0.2),
            ), patch(
                'app.views.main_window.QMessageBox.question',
                return_value=QMessageBox.StandardButton.Yes,
            ), patch('app.views.locacoes_page.QMessageBox.information'):
                window.locacoes_page.exportar_relatorio()
                thread = window.locacoes_page.thread_exportacao
                self.assertTrue(thread.isRunning())

                window.closeEvent(evento)

                self.assertFalse(thread.isRunning())
                evento.accept.assert_called_once()
                evento.ignore.assert_not_called()
                self.app.processEvents()
                self.assertIsNone(window.locacoes_page.thread_exportacao)


if __name__ == '__main__':
    unittest.main()
