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


if __name__ == '__main__':
    unittest.main()
