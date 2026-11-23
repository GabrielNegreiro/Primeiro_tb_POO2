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

from app.network.api_client import ApiClient
from app.services.filme_api_service import FilmeApiService
from app.services.locacao_api_service import LocacaoApiService
from app.services.locacao_service import LocacaoService
from app.views.dashboard_page import DashboardPage
from app.views.filmes_page import FilmesPage
from app.views.locacoes_page import LocacoesPage
from app.views.sobre_dialog import SobreDialog
from app.workers.filme_loader_thread import FilmeLoaderThread
from app.workers.locacao_loader_thread import LocacaoLoaderThread


class MainWindow(QMainWindow):
    MENSAGEM_LOCACOES_PENDENTES = (
        'As locacoes locais estao temporariamente desabilitadas no modo HTTP. '
        'A integracao com a API de locacoes deve ser concluida antes de alterar '
        'a disponibilidade dos filmes. Nenhum dado CSV foi removido.'
    )

    def __init__(self, api_client=None, filme_service=None, locacao_service=None):
        super().__init__()
        self.setWindowTitle('Locadora de Filmes')
        self.resize(900, 600)

        self.api_client = api_client
        if filme_service is None:
            self.api_client = self.api_client or ApiClient()
            filme_service = FilmeApiService(self.api_client)
        self.filme_service = filme_service
        self.filme_loader_thread = None
        self.locacao_loader_thread = None

        # Modo HTTP: locacoes vem da API. Sem cliente HTTP nem servico
        # injetado, o legado fica isolado e as acoes continuam bloqueadas.
        if locacao_service is None and self.api_client is not None:
            locacao_service = LocacaoApiService(
                self.api_client, self.filme_service
            )
        self.modo_http_locacoes = locacao_service is not None
        self.locacao_service = (
            locacao_service if self.modo_http_locacoes else LocacaoService()
        )

        self.dashboard_page = DashboardPage(self.locacao_service, self.filme_service)
        self.filmes_page = FilmesPage(self.filme_service)
        self.locacoes_page = LocacoesPage(self.locacao_service, self.filme_service)
        if not self.modo_http_locacoes:
            self.dashboard_page.definir_locacoes_indisponiveis(
                self.MENSAGEM_LOCACOES_PENDENTES
            )
            self.locacoes_page.ativar_modo_integracao_pendente(
                self.MENSAGEM_LOCACOES_PENDENTES
            )

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
        self._iniciar_carregamento_filmes()

    def _criar_acoes(self):
        self.acao_inicio = QAction('Inicio', self)
        self.acao_filmes = QAction('Filmes', self)
        self.acao_locacoes = QAction('Locacoes', self)
        self.acao_novo_filme = QAction('Novo Filme', self)
        self.acao_nova_locacao = QAction('Nova Locacao', self)
        if not self.modo_http_locacoes:
            self.acao_nova_locacao.setEnabled(False)
            self.acao_nova_locacao.setToolTip(
                self.MENSAGEM_LOCACOES_PENDENTES
            )
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
        self.filmes_page.filme_cadastrado.connect(
            self._atualizar_dados_locais
        )
        self.filmes_page.filme_atualizado.connect(
            self._atualizar_dados_locais
        )
        self.filmes_page.filme_excluido.connect(
            self._atualizar_dados_locais
        )
        if self.modo_http_locacoes:
            # O worker ja recarregou o acervo; basta redesenhar as telas.
            self.locacoes_page.locacoes_alteradas.connect(
                self._on_locacoes_alteradas
            )
        else:
            self.locacoes_page.locacoes_alteradas.connect(self.atualizar_tudo)

    def _iniciar_carregamento_filmes(self):
        if self.filmes_page.operacao_em_andamento():
            self.statusBar().showMessage(
                'Aguarde a operacao de filmes terminar.'
            )
            return False
        if self.locacoes_page.operacao_em_andamento():
            self.statusBar().showMessage(
                'Aguarde a operacao de locacoes terminar.'
            )
            return False
        if (
            self.filme_loader_thread is not None
            and self.filme_loader_thread.isRunning()
        ):
            self.statusBar().showMessage(
                'A atualizacao do acervo ja esta em andamento.'
            )
            return False

        thread_anterior = self.filme_loader_thread
        if thread_anterior is not None:
            thread_anterior.deleteLater()

        self.statusBar().showMessage('Carregando acervo...')
        self.filmes_page.set_carregando(True)
        self.filme_loader_thread = FilmeLoaderThread(
            self.filme_service,
            self,
        )
        self.filme_loader_thread.carregado.connect(
            self._on_filmes_carregados
        )
        self.filme_loader_thread.erro.connect(
            self._on_erro_carregamento_filmes
        )
        thread_atual = self.filme_loader_thread
        self.filme_loader_thread.finished.connect(
            lambda: self._finalizar_carregamento_filmes(thread_atual)
        )
        self.filme_loader_thread.start()
        self._iniciar_carregamento_locacoes()
        return True

    def _iniciar_carregamento_locacoes(self):
        """Carrega as locacoes da API em um worker (somente modo HTTP)."""
        if not self.modo_http_locacoes:
            return False
        if self.locacoes_page.operacao_em_andamento():
            return False
        if (
            self.locacao_loader_thread is not None
            and self.locacao_loader_thread.isRunning()
        ):
            return False

        self.locacoes_page.set_carregando(True)
        thread = LocacaoLoaderThread(self.locacao_service, self)
        self.locacao_loader_thread = thread
        thread.carregado.connect(self._on_locacoes_carregadas)
        thread.erro.connect(self._on_erro_carregamento_locacoes)
        thread.finished.connect(
            lambda: self._finalizar_carregamento_locacoes(thread)
        )
        thread.start()
        return True

    def _on_filmes_carregados(self, filmes):
        self.filme_service.aplicar_filmes_carregados(filmes)
        self.filmes_page.carregar_filmes()
        self.locacoes_page.atualizar_tabela()
        self.dashboard_page.atualizar_resumo()
        self.statusBar().showMessage('Acervo carregado.', 3000)

    def _on_erro_carregamento_filmes(self, mensagem):
        self.statusBar().showMessage('Falha ao carregar o acervo.')
        QMessageBox.warning(
            self,
            'Erro ao carregar acervo',
            f'Nao foi possivel carregar o acervo de filmes.\n\n{mensagem}',
        )

    def _on_locacoes_carregadas(self, locacoes):
        self.locacao_service.aplicar_locacoes_carregadas(locacoes)
        self.dashboard_page.definir_locacoes_integradas()
        self.locacoes_page.atualizar_tabela()
        self.statusBar().showMessage('Locacoes carregadas.', 3000)

    def _on_erro_carregamento_locacoes(self, mensagem):
        self.statusBar().showMessage('Falha ao carregar as locacoes.')
        self.dashboard_page.definir_locacoes_indisponiveis(
            'Nao foi possivel carregar as locações da API.'
        )
        QMessageBox.warning(
            self,
            'Erro ao carregar locacoes',
            f'Nao foi possivel carregar as locacoes.\n\n{mensagem}',
        )

    def _finalizar_carregamento_filmes(self, thread):
        """Restaura a tela e libera a referencia da thread concluida."""
        if self.filme_loader_thread is thread:
            self.filme_loader_thread = None
            self.filmes_page.set_carregando(False)
        thread.deleteLater()

    def _finalizar_carregamento_locacoes(self, thread):
        """Reabilita a tela de locacoes e libera o worker concluido."""
        if self.locacao_loader_thread is thread:
            self.locacao_loader_thread = None
            self.locacoes_page.set_carregando(False)
        thread.deleteLater()

    def _atualizar_dados_locais(self):
        """Atualiza consumidores do cache sem realizar HTTP na GUI."""
        self.locacoes_page.atualizar_tabela()
        self.dashboard_page.atualizar_resumo()

    def _on_locacoes_alteradas(self):
        """Redesenha filmes, locacoes e dashboard a partir dos caches."""
        self.filmes_page.carregar_filmes()
        self._atualizar_dados_locais()

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

    def atualizar_tudo(self):
        self._atualizar_dados_locais()
        return self._iniciar_carregamento_filmes()

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
            if (
                self.filme_loader_thread is not None
                and self.filme_loader_thread.isRunning()
            ):
                self.statusBar().showMessage('Aguardando o carregamento terminar...')
                if not self.filme_loader_thread.wait(3000):
                    QMessageBox.information(
                        self,
                        'Carregamento em andamento',
                        'Aguarde o carregamento do acervo terminar para sair.',
                    )
                    event.ignore()
                    return
            if (
                self.locacao_loader_thread is not None
                and self.locacao_loader_thread.isRunning()
            ):
                self.statusBar().showMessage(
                    'Aguardando o carregamento das locacoes...'
                )
                if not self.locacao_loader_thread.wait(3000):
                    QMessageBox.information(
                        self,
                        'Carregamento em andamento',
                        'Aguarde o carregamento das locacoes terminar para sair.',
                    )
                    event.ignore()
                    return
            if self.filmes_page.operacao_em_andamento():
                self.statusBar().showMessage(
                    'Aguardando a operacao de filmes terminar...'
                )
                if not self.filmes_page.aguardar_operacao(3000):
                    QMessageBox.information(
                        self,
                        'Operacao em andamento',
                        'Aguarde a operacao de filmes terminar para sair.',
                    )
                    event.ignore()
                    return
            if self.locacoes_page.operacao_em_andamento():
                self.statusBar().showMessage(
                    'Aguardando a operacao de locacoes terminar...'
                )
                if not self.locacoes_page.aguardar_operacao(3000):
                    QMessageBox.information(
                        self,
                        'Operacao em andamento',
                        'Aguarde a operacao de locacoes terminar para sair.',
                    )
                    event.ignore()
                    return
            if self.locacoes_page.exportacao_em_andamento():
                self.statusBar().showMessage('Aguardando a exportacao terminar...')
                if not self.locacoes_page.aguardar_exportacao(3000):
                    QMessageBox.information(
                        self,
                        'Exportacao em andamento',
                        'Aguarde a exportacao do relatorio terminar para sair.',
                    )
                    event.ignore()
                    return
            fechar = getattr(self.filme_service, 'fechar', None)
            if fechar is not None:
                fechar()
            event.accept()
        else:
            event.ignore()