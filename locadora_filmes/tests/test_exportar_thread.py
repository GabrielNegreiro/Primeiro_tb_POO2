import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from app.views.exportar_thread import ExportarRelatorioThread


class ExportarRelatorioThreadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.threads = []

    def tearDown(self):
        for thread in self.threads:
            if thread.isRunning():
                self.assertTrue(thread.wait(5000))
            thread.deleteLater()
        self.app.processEvents()
        self.diretorio_temporario.cleanup()

    def criar_thread(self, caminho=None):
        caminho = caminho or Path(self.diretorio_temporario.name) / 'relatorio.txt'
        thread = ExportarRelatorioThread([], str(caminho))
        self.threads.append(thread)
        return thread

    def executar_thread(self, thread):
        thread.start()
        self.assertTrue(thread.wait(5000))
        self.app.processEvents()
        self.assertFalse(thread.isRunning())

    def test_criacao(self):
        caminho = Path(self.diretorio_temporario.name) / 'relatorio.txt'

        thread = self.criar_thread(caminho)

        self.assertEqual(thread.locacoes, [])
        self.assertEqual(thread.caminho, str(caminho))
        self.assertFalse(thread.isRunning())

    def test_execucao_normal_emite_concluido_e_termina(self):
        caminho = Path(self.diretorio_temporario.name) / 'relatorio.txt'
        thread = self.criar_thread(caminho)
        concluido = QSignalSpy(thread.concluido)
        falhou = QSignalSpy(thread.falhou)

        self.executar_thread(thread)

        self.assertTrue(caminho.exists())
        self.assertEqual(concluido.count(), 1)
        self.assertEqual(concluido.at(0)[0], str(caminho))
        self.assertEqual(falhou.count(), 0)

    def test_erro_de_escrita_emite_falhou_e_termina(self):
        thread = self.criar_thread()
        concluido = QSignalSpy(thread.concluido)
        falhou = QSignalSpy(thread.falhou)

        with patch(
            'app.views.exportar_thread.RelatorioService.exportar_txt',
            side_effect=OSError('falha de teste'),
        ):
            self.executar_thread(thread)

        self.assertEqual(concluido.count(), 0)
        self.assertEqual(falhou.count(), 1)
        self.assertIn('falha de teste', falhou.at(0)[0])


if __name__ == '__main__':
    unittest.main()
