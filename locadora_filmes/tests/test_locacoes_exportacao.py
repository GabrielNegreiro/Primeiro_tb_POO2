import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.services.locacao_service import LocacaoService
from app.views.locacoes_page import LocacoesPage


class LocacoesExportacaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.pagina = LocacoesPage(LocacaoService(), Mock())

    def tearDown(self):
        if self.pagina.exportacao_em_andamento():
            self.assertTrue(self.pagina.aguardar_exportacao(5000))
        self.app.processEvents()
        self.pagina.deleteLater()
        self.app.processEvents()
        self.diretorio_temporario.cleanup()

    def test_finalizacao_limpa_referencia_e_reabilita_botao(self):
        caminho = Path(self.diretorio_temporario.name) / 'relatorio.txt'
        with patch(
            'app.views.locacoes_page.QFileDialog.getSaveFileName',
            return_value=(str(caminho), 'Arquivo de texto (*.txt)'),
        ), patch('app.views.locacoes_page.QMessageBox.information'):
            self.pagina.exportar_relatorio()
            thread = self.pagina.thread_exportacao
            self.assertIsNotNone(thread)
            self.assertFalse(self.pagina.botao_exportar.isEnabled())
            self.assertTrue(thread.wait(5000))
            self.app.processEvents()

        self.assertTrue(caminho.exists())
        self.assertIsNone(self.pagina.thread_exportacao)
        self.assertTrue(self.pagina.botao_exportar.isEnabled())

    def test_aguardar_exportacao_respeita_resultado_da_thread(self):
        thread = Mock()
        thread.isRunning.return_value = True
        thread.wait.return_value = False
        self.pagina.thread_exportacao = thread

        terminou = self.pagina.aguardar_exportacao(250)

        self.assertFalse(terminou)
        thread.wait.assert_called_once_with(250)
        self.pagina.thread_exportacao = None


if __name__ == '__main__':
    unittest.main()
