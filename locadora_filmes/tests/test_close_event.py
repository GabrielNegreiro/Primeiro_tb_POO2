import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QMessageBox

from app.views.main_window import MainWindow


class CloseEventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_close_event_yes_aceita(self):
        window = MainWindow()
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window.closeEvent(evento)

        evento.accept.assert_called_once()
        evento.ignore.assert_not_called()

    def test_close_event_no_ignora(self):
        window = MainWindow()
        evento = Mock()

        with patch(
            'app.views.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.No,
        ):
            window.closeEvent(evento)

        evento.ignore.assert_called_once()
        evento.accept.assert_not_called()

    def test_close_event_aguarda_thread_em_execucao(self):
        window = MainWindow()
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
        window = MainWindow()
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


if __name__ == '__main__':
    unittest.main()
