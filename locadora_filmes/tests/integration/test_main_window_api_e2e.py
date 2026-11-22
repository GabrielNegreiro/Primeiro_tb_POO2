import os
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.network.api_client import ApiClient
from app.services.filme_api_service import FilmeApiService
from app.views.main_window import MainWindow


@unittest.skipUnless(
    os.getenv('RUN_DESKTOP_API_INTEGRATION') == '1',
    'Requer api_test e RUN_DESKTOP_API_INTEGRATION=1.',
)
class MainWindowApiE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def processar_eventos(self):
        for _ in range(10):
            self.app.processEvents()

    def aguardar_carregamento(self, window):
        thread = window.filme_loader_thread
        if thread is not None:
            self.assertTrue(thread.wait(5000))
        self.processar_eventos()

    def aguardar_operacao(self, page):
        thread = page.operacao_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.processar_eventos()

    def test_interface_executa_crud_sem_bloquear_handlers(self):
        base_url = os.getenv(
            'LOCADORA_TEST_API_BASE_URL',
            'http://127.0.0.1:8001',
        )
        client = ApiClient(base_url)
        service = FilmeApiService(client)
        window = MainWindow(api_client=client, filme_service=service)
        filme_id = None
        try:
            self.aguardar_carregamento(window)
            page = window.filmes_page
            titulo = f'Interface E2E {uuid.uuid4()}'

            with patch('app.views.filmes_page.QMessageBox.information'):
                self.assertTrue(page._executar_operacao(
                    'cadastro',
                    service.adicionar_filme,
                    titulo=titulo,
                    genero='Teste',
                    ano=2026,
                    duracao=92,
                    disponivel=True,
                ))
                self.aguardar_operacao(page)

            criado = next(
                filme for filme in service.filmes if filme.titulo == titulo
            )
            filme_id = criado.id
            self.assertTrue(any(
                page.tabela.item(linha, 1).text() == titulo
                for linha in range(page.tabela.rowCount())
            ))

            with patch('app.views.filmes_page.QMessageBox.information'):
                self.assertTrue(page._executar_operacao(
                    'edicao',
                    service.atualizar_filme,
                    filme_id,
                    titulo=f'{titulo} Atualizado',
                    genero='Teste Integracao',
                    ano=2026,
                    duracao=93,
                    disponivel=False,
                ))
                self.aguardar_operacao(page)

            page.pesquisar('Atualizado')
            self.assertEqual(page.tabela.rowCount(), 1)
            self.assertEqual(page.tabela.item(0, 4).text(), '93 min')

            with patch('app.views.filmes_page.QMessageBox.information'):
                self.assertTrue(page._executar_operacao(
                    'exclusao',
                    service.remover_filme,
                    filme_id,
                ))
                self.aguardar_operacao(page)
            filme_id = None
            self.assertEqual(page.tabela.rowCount(), 0)
        finally:
            if page := getattr(window, 'filmes_page', None):
                if page.operacao_em_andamento():
                    page.aguardar_operacao(5000)
            if filme_id is not None:
                try:
                    client.delete(f'/filmes/{filme_id}')
                except Exception:
                    pass
            client.close()
            window.deleteLater()
            self.processar_eventos()


if __name__ == '__main__':
    unittest.main()
