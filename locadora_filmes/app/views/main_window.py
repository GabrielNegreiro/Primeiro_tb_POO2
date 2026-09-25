from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from app.services.filme_service import FilmeService
from app.services.locacao_service import LocacaoService
from app.views.dashboard_page import DashboardPage
from app.views.filmes_page import FilmesPage
from app.views.locacoes_page import LocacoesPage
from app.views.sobre_dialog import SobreDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Locadora de Filmes')
        self.resize(900, 600)

        self.filme_service = FilmeService()
        self.locacao_service = LocacaoService()

        self.dashboard_page = DashboardPage(self.locacao_service, self.filme_service)
        self.filmes_page = FilmesPage(self.filme_service)
        self.locacoes_page = LocacoesPage(self.locacao_service, self.filme_service)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.filmes_page)
        self.stack.addWidget(self.locacoes_page)

        self.navegacao = QListWidget()
        for texto in ('Inicio', 'Filmes', 'Locacoes'):
            self.navegacao.addItem(QListWidgetItem(texto))
        self.navegacao.setFixedWidth(150)
        self.navegacao.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.navegacao.setCurrentRow(0)

        central = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.navegacao)
        layout.addWidget(self.stack)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._criar_acoes()
        self._criar_menu()
        self._criar_toolbar()
        self._conectar_integracao()

    def _criar_acoes(self):
        self.acao_inicio = QAction('Inicio', self)
        self.acao_filmes = QAction('Filmes', self)
        self.acao_locacoes = QAction('Locacoes', self)
        self.acao_novo_filme = QAction('Novo Filme', self)
        self.acao_nova_locacao = QAction('Nova Locacao', self)
        self.acao_atualizar = QAction('Atualizar', self)
        self.acao_sobre = QAction('Sobre', self)
        self.acao_sair = QAction('Sair', self)

        self.acao_inicio.triggered.connect(self.ir_inicio)
        self.acao_filmes.triggered.connect(self.ir_filmes)
        self.acao_locacoes.triggered.connect(self.ir_locacoes)
        self.acao_novo_filme.triggered.connect(self.novo_filme)
        self.acao_nova_locacao.triggered.connect(self.nova_locacao)
        self.acao_atualizar.triggered.connect(self.atualizar_tudo)
        self.acao_sobre.triggered.connect(self.mostrar_sobre)
        self.acao_sair.triggered.connect(self.close)

    def _criar_menu(self):
        menu_arquivo = self.menuBar().addMenu('Arquivo')
        menu_arquivo.addAction(self.acao_sair)

        menu_filmes = self.menuBar().addMenu('Filmes')
        menu_filmes.addAction(self.acao_novo_filme)

        menu_locacoes = self.menuBar().addMenu('Locacoes')
        menu_locacoes.addAction(self.acao_nova_locacao)

        menu_ajuda = self.menuBar().addMenu('Ajuda')
        menu_ajuda.addAction(self.acao_sobre)

    def _criar_toolbar(self):
        # TOOLBAR: acoes rapidas da aplicacao.
        toolbar = QToolBar('Acoes principais', self)
        toolbar.addAction(self.acao_inicio)
        toolbar.addAction(self.acao_filmes)
        toolbar.addAction(self.acao_locacoes)
        toolbar.addSeparator()
        toolbar.addAction(self.acao_novo_filme)
        toolbar.addAction(self.acao_nova_locacao)
        toolbar.addAction(self.acao_atualizar)
        toolbar.addSeparator()
        toolbar.addAction(self.acao_sair)
        self.addToolBar(toolbar)
        self.toolbar = toolbar

    def _conectar_integracao(self):
        self.filmes_page.filme_cadastrado.connect(self.atualizar_tudo)
        self.filmes_page.filme_atualizado.connect(self.atualizar_tudo)
        self.filmes_page.filme_excluido.connect(self.atualizar_tudo)
        self.locacoes_page.locacoes_alteradas.connect(self.atualizar_tudo)

    def ir_inicio(self):
        self.navegacao.setCurrentRow(0)

    def ir_filmes(self):
        self.navegacao.setCurrentRow(1)

    def ir_locacoes(self):
        self.navegacao.setCurrentRow(2)

    def novo_filme(self):
        self.ir_filmes()
        self.filmes_page.abrir_cadastro()

    def nova_locacao(self):
        self.ir_locacoes()
        self.locacoes_page.abrir_nova_locacao()
        self.atualizar_tudo()

    def atualizar_tudo(self):
        self.filmes_page.carregar_filmes()
        self.locacoes_page.atualizar_tabela()
        self.dashboard_page.atualizar_resumo()

    def mostrar_sobre(self):
        dialog = SobreDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        # EVENTO: intercepta tentativa de fechamento da MainWindow.
        resposta = QMessageBox.question(
            self,
            'Sair',
            'Deseja realmente sair?',
        )
        if resposta == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
