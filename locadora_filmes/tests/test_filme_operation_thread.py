import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QSignalSpy

from app.workers.filme_operation_thread import FilmeOperationThread


class FilmeOperationThreadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def executar(self, thread):
        thread.start()
        self.assertTrue(thread.wait(3000))
        self.app.processEvents()

    def test_resultado_e_emitido(self):
        thread = FilmeOperationThread(lambda valor: valor * 2, 4)
        sucesso = QSignalSpy(thread.sucesso)
        erro = QSignalSpy(thread.erro)

        self.executar(thread)

        self.assertEqual(sucesso.count(), 1)
        self.assertEqual(sucesso.at(0)[0], 8)
        self.assertEqual(erro.count(), 0)

    def test_excecao_e_convertida_em_sinal(self):
        def falhar():
            raise RuntimeError('API indisponivel')

        thread = FilmeOperationThread(falhar)
        sucesso = QSignalSpy(thread.sucesso)
        erro = QSignalSpy(thread.erro)

        self.executar(thread)

        self.assertEqual(sucesso.count(), 0)
        self.assertEqual(erro.count(), 1)
        self.assertIn('API indisponivel', erro.at(0)[0])


if __name__ == '__main__':
    unittest.main()
