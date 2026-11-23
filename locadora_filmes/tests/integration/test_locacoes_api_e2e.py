import os
import tempfile
import unittest
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QMessageBox

from app.network.api_client import ApiClient, ApiHttpError
from app.services.filme_api_service import FilmeApiService
from app.services.locacao_api_service import LocacaoApiService
from app.services.relatorio_service import RelatorioService
from app.views.main_window import MainWindow

BASE_URL = os.getenv('LOCADORA_TEST_API_BASE_URL', 'http://127.0.0.1:8001')


def _limpar(client, locacoes_ids, filme_id):
    """Remove os dados do teste; falhas de limpeza nao mascaram o teste."""
    for identificador in locacoes_ids:
        for metodo, caminho, extra in (
            (client.post, f'/locacoes/{identificador}/devolucao', {'json': {}}),
            (client.delete, f'/locacoes/{identificador}', {}),
        ):
            try:
                metodo(caminho, **extra)
            except Exception:
                pass
    if filme_id is not None:
        try:
            client.delete(f'/filmes/{filme_id}')
        except Exception:
            pass


@unittest.skipUnless(
    os.getenv('RUN_DESKTOP_API_INTEGRATION') == '1',
    'Requer api_test e RUN_DESKTOP_API_INTEGRATION=1.',
)
class LocacoesDesktopApiE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def processar_eventos(self):
        for _ in range(10):
            self.app.processEvents()

    def aguardar_loaders(self, window):
        for thread in (window.filme_loader_thread, window.locacao_loader_thread):
            if thread is not None:
                self.assertTrue(thread.wait(5000))
        self.processar_eventos()

    def aguardar_operacao(self, page):
        thread = page.operacao_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(5000))
        self.processar_eventos()
        self.assertIsNone(page.operacao_thread)

    @staticmethod
    def linhas_com_titulo(page, titulo):
        return [
            linha
            for linha in range(page.tabela.rowCount())
            if page.tabela.item(linha, 0).text() == titulo
        ]

    def test_ciclo_de_locacao_pela_interface(self):
        client = ApiClient(BASE_URL)
        service = FilmeApiService(client)
        filme_id = None
        locacoes_ids = []
        with patch.object(QMessageBox, 'warning') as aviso, patch.object(
            QMessageBox, 'information'
        ):
            window = MainWindow(api_client=client, filme_service=service)
            try:
                self.aguardar_loaders(window)
                page = window.locacoes_page
                dashboard = window.dashboard_page
                locacao_service = window.locacao_service
                self.assertTrue(window.modo_http_locacoes)
                self.assertTrue(locacao_service.carregado)

                ativas_antes = len(locacao_service.listar_ativas())
                self.assertEqual(dashboard.label_ativas.text(), str(ativas_antes))

                titulo = f'Locacao E2E {uuid.uuid4()}'
                filme = service.adicionar_filme(
                    titulo=titulo,
                    genero='Teste',
                    ano=2026,
                    duracao=90,
                    disponivel=True,
                )
                filme_id = filme.id

                # 1) cadastro pela pagina: filme passa a indisponivel
                self.assertTrue(page._executar_operacao(
                    'cadastro',
                    locacao_service.criar_locacao,
                    filme,
                    'Cliente E2E',
                    dias_previstos=7,
                ))
                self.aguardar_operacao(page)
                primeira = next(
                    item
                    for item in locacao_service.listar_todas()
                    if item.filme_id == filme_id
                )
                locacoes_ids.append(primeira.id)
                self.assertEqual(primeira.status, 'Em aberto')
                self.assertEqual(len(self.linhas_com_titulo(page, titulo)), 1)
                self.assertFalse(service.obter_filme(filme_id).disponivel)
                self.assertNotIn(
                    filme_id, [f.id for f in service.listar_disponiveis()]
                )
                self.assertEqual(
                    dashboard.label_ativas.text(), str(ativas_antes + 1)
                )

                # 2) segunda locacao do mesmo filme e rejeitada pela API
                with self.assertRaises(ApiHttpError):
                    locacao_service.criar_locacao(
                        filme, 'Outro Cliente', dias_previstos=3
                    )
                self.assertEqual(
                    len([
                        item
                        for item in locacao_service.listar_todas()
                        if item.filme_id == filme_id
                    ]),
                    1,
                )

                # 3) devolucao pelo handler da pagina, com linha selecionada
                linha = self.linhas_com_titulo(page, titulo)[0]
                page.tabela.setCurrentCell(linha, 0)
                page.devolver_selecionada()
                self.aguardar_operacao(page)
                devolvida = locacao_service.obter_locacao(primeira.id)
                self.assertEqual(devolvida.status, 'Devolvido')
                self.assertIsNotNone(devolvida.data_devolucao_real)
                self.assertTrue(service.obter_filme(filme_id).disponivel)
                self.assertEqual(dashboard.label_ativas.text(), str(ativas_antes))

                # 4) alugar de novo o mesmo filme
                self.assertTrue(page._executar_operacao(
                    'cadastro',
                    locacao_service.criar_locacao,
                    service.obter_filme(filme_id),
                    'Cliente E2E 2',
                    dias_previstos=5,
                ))
                self.aguardar_operacao(page)
                segunda = next(
                    item
                    for item in locacao_service.listar_ativas()
                    if item.filme_id == filme_id
                )
                locacoes_ids.append(segunda.id)
                self.assertNotEqual(segunda.id, primeira.id)

                # 5) persistencia: cliente e servicos novos releem do PostgreSQL
                novo_client = ApiClient(BASE_URL)
                try:
                    novos_filmes = FilmeApiService(novo_client)
                    novas_locacoes = LocacaoApiService(novo_client, novos_filmes)
                    novos_filmes.carregar_filmes()
                    recarregadas = {
                        item.id: item for item in novas_locacoes.carregar_locacoes()
                    }
                finally:
                    novo_client.close()
                self.assertEqual(recarregadas[primeira.id].status, 'Devolvido')
                self.assertEqual(recarregadas[segunda.id].status, 'Em aberto')
                self.assertEqual(recarregadas[segunda.id].titulo_filme, titulo)

                # 6) exportacao TXT com os dados vindos da API
                todas = locacao_service.listar_todas()
                with tempfile.TemporaryDirectory() as pasta:
                    caminho = Path(pasta) / 'relatorio.txt'
                    RelatorioService().exportar_txt(todas, caminho)
                    texto = caminho.read_text(encoding='utf-8')
                self.assertIn(f'Filme: {titulo}', texto)
                self.assertIn('Cliente: Cliente E2E 2', texto)
                self.assertIn(f'Total de locacoes: {len(todas)}', texto)

                # nenhum aviso de erro apareceu durante o ciclo
                self.assertEqual(aviso.call_args_list, [])
            finally:
                if window.locacoes_page.operacao_em_andamento():
                    window.locacoes_page.aguardar_operacao(5000)
                _limpar(client, locacoes_ids, filme_id)
                client.close()
                window.deleteLater()
                self.processar_eventos()

    def test_edicao_devolucao_e_exclusao_pelo_servico(self):
        client = ApiClient(BASE_URL)
        filmes = FilmeApiService(client)
        locacoes = LocacaoApiService(client, filmes)
        filme_id = None
        locacoes_ids = []
        try:
            filmes.carregar_filmes()
            filme = filmes.adicionar_filme(
                titulo=f'Servico E2E {uuid.uuid4()}',
                genero='Teste',
                ano=2026,
                duracao=95,
                disponivel=True,
            )
            filme_id = filme.id
            criada = locacoes.criar_locacao(filme, 'Cliente Servico', dias_previstos=7)
            locacoes_ids.append(criada.id)
            self.assertEqual(
                criada.data_devolucao_prevista - criada.data_locacao,
                timedelta(days=7),
            )

            editada = locacoes.atualizar_locacao(
                criada.id, filme, 'Cliente Editado', 10
            )
            self.assertEqual(editada.cliente_nome, 'Cliente Editado')
            self.assertEqual(
                editada.data_devolucao_prevista - editada.data_locacao,
                timedelta(days=10),
            )

            devolvida = locacoes.devolver_locacao(criada.id)
            self.assertEqual(devolvida.status, 'Devolvido')

            locacoes.excluir_locacao(criada.id)
            locacoes_ids.clear()
            self.assertIsNone(locacoes.obter_locacao(criada.id))
            with self.assertRaises(ApiHttpError) as contexto:
                locacoes.buscar_por_id(criada.id)
            self.assertEqual(contexto.exception.status_code, 404)
        finally:
            _limpar(client, locacoes_ids, filme_id)
            client.close()

    def test_fechar_janela_com_workers_de_locacao_ativos(self):
        client = ApiClient(BASE_URL)
        service = FilmeApiService(client)
        with patch.object(QMessageBox, 'warning'), patch.object(
            QMessageBox,
            'question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window = MainWindow(api_client=client, filme_service=service)
            filmes_thread = window.filme_loader_thread
            locacoes_thread = window.locacao_loader_thread
            self.assertIsNotNone(filmes_thread)
            self.assertIsNotNone(locacoes_thread)
            # o closeEvent espera os loaders e fecha o cliente HTTP
            self.assertTrue(window.close())
            self.assertFalse(filmes_thread.isRunning())
            self.assertFalse(locacoes_thread.isRunning())
        self.processar_eventos()
        window.deleteLater()
        self.processar_eventos()


if __name__ == '__main__':
    unittest.main()