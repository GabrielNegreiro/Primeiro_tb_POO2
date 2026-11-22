import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenuBar, QStackedWidget, QToolBar

from app.models.filme import Filme
from app.views.dashboard_page import DashboardPage
from app.views.filmes_page import FilmesPage
from app.views.locacoes_page import LocacoesPage
from app.views.main_window import MainWindow


class FilmeApiServiceFake:
    def __init__(self, filmes):
        self.fonte = list(filmes)
        self.filmes = []
        self.carregamentos = 0
        self.fechado = False

    def carregar_filmes(self):
        self.carregamentos += 1
        self.aplicar_filmes_carregados(self.fonte)
        return self.listar_filmes()

    def aplicar_filmes_carregados(self, filmes):
        self.filmes = list(filmes)

    def listar_filmes(self):
        return list(self.filmes)

    def buscar_filmes(self, texto):
        termo = texto.strip().lower()
        return [
            filme
            for filme in self.filmes
            if not termo
            or termo in filme.titulo.lower()
            or termo in filme.genero.lower()
            or termo in str(filme.ano)
        ]

    def obter_filme(self, filme_id):
        return next(
            (filme for filme in self.filmes if filme.id == filme_id),
            None,
        )

    def listar_disponiveis(self):
        return [filme for filme in self.filmes if filme.disponivel]

    def fechar(self):
        self.fechado = True


class FilmeLoaderThreadFake(QObject):
    carregado = Signal(object)
    erro = Signal(str)
    finished = Signal()
    instancias = []

    def __init__(self, fonte, parent=None):
        super().__init__(parent)
        self.fonte = fonte
        self.iniciada = False
        self.__class__.instancias.append(self)

    def start(self):
        self.iniciada = True
        try:
            filmes = self.fonte.carregar_filmes()
        except Exception as excecao:
            self.erro.emit(str(excecao))
        else:
            self.carregado.emit(filmes)
        self.finished.emit()

    def isRunning(self):
        return False

    def wait(self, _tempo=0):
        return True


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        FilmeLoaderThreadFake.instancias.clear()
        self.filmes_persistidos = [
            Filme(3, 'Interestelar', 'Ficcao', 2014, 169, True),
            Filme(7, 'Cidade de Deus', 'Drama', 2002, 130, False),
        ]
        self.service = FilmeApiServiceFake(self.filmes_persistidos)
        self.loader_patch = patch(
            'app.views.main_window.FilmeLoaderThread',
            FilmeLoaderThreadFake,
        )
        self.loader_patch.start()
        self.addCleanup(self.loader_patch.stop)

        self.window = MainWindow(filme_service=self.service)
        self.loader = FilmeLoaderThreadFake.instancias[-1]

    def tearDown(self):
        self.window.deleteLater()
        self.app.processEvents()

    def test_paginas_e_stack(self):
        self.assertIsInstance(self.window.stack, QStackedWidget)
        self.assertIsInstance(self.window.dashboard_page, DashboardPage)
        self.assertIsInstance(self.window.filmes_page, FilmesPage)
        self.assertIsInstance(self.window.locacoes_page, LocacoesPage)

    def test_service_http_unico_e_loader(self):
        self.assertIs(self.window.filmes_page.filme_service, self.service)
        self.assertIs(self.window.dashboard_page.filme_service, self.service)
        self.assertIs(self.window.locacoes_page.filme_service, self.service)
        self.assertTrue(self.loader.iniciada)
        self.assertEqual(self.service.carregamentos, 1)

    def test_carregamento_inicial_atualiza_tela_e_dashboard(self):
        self.assertEqual(
            self.service.listar_filmes(),
            self.filmes_persistidos,
        )
        self.assertEqual(self.window.filmes_page.tabela.rowCount(), 2)
        self.assertEqual(
            self.window.dashboard_page.label_disponiveis.text(),
            '1',
        )

    def test_signal_de_sucesso_atualiza_service_e_paginas(self):
        novos_filmes = [
            Filme(10, 'Novo Acervo', 'Drama', 2026, 100, True),
        ]

        self.loader.carregado.emit(novos_filmes)

        self.assertEqual(self.service.listar_filmes(), novos_filmes)
        self.assertEqual(self.window.filmes_page.tabela.rowCount(), 1)
        self.assertEqual(
            self.window.filmes_page.tabela.item(0, 1).text(),
            'Novo Acervo',
        )

    def test_signal_de_erro_exibe_aviso_sem_fallback(self):
        acervo_anterior = self.service.listar_filmes()
        with patch('app.views.main_window.QMessageBox.warning') as warning:
            self.loader.erro.emit('API indisponivel')

        warning.assert_called_once()
        self.assertEqual(self.service.listar_filmes(), acervo_anterior)
        self.assertIn('API indisponivel', warning.call_args.args[2])

    def test_navegacao_menu_toolbar_e_sobre(self):
        self.window.ir_filmes()
        self.assertEqual(
            self.window.stack.currentWidget(),
            self.window.filmes_page,
        )
        self.window.ir_locacoes()
        self.assertEqual(
            self.window.stack.currentWidget(),
            self.window.locacoes_page,
        )
        self.assertIsInstance(self.window.menuBar(), QMenuBar)
        self.assertTrue(self.window.findChildren(QToolBar))
        with patch('app.views.main_window.SobreDialog') as sobre_dialog:
            self.window.mostrar_sobre()
            sobre_dialog.assert_called_once_with(self.window)

    def test_atualizar_dispara_novo_carregamento_sem_bloquear(self):
        self.assertTrue(self.window.atualizar_tudo())
        self.assertEqual(self.service.carregamentos, 2)
        self.assertEqual(len(FilmeLoaderThreadFake.instancias), 2)

    def test_locacoes_ficam_preservadas_e_bloqueadas_no_modo_http(self):
        self.assertTrue(self.window.locacoes_page.modo_integracao_pendente)
        self.assertFalse(self.window.locacoes_page.botao_nova.isEnabled())
        self.assertFalse(self.window.acao_nova_locacao.isEnabled())
        self.assertEqual(self.window.dashboard_page.label_ativas.text(), '-')
        self.assertIn(
            'Nenhum dado CSV foi removido',
            self.window.locacoes_page.label_integracao.text(),
        )


if __name__ == '__main__':
    unittest.main()
