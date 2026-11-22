from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.views.filme_dialog import FilmeDialog
from app.widgets.search_bar import SearchBar
from app.workers.filme_operation_thread import FilmeOperationThread


class FilmesPage(QWidget):
    filme_cadastrado = Signal()
    filme_atualizado = Signal()
    filme_excluido = Signal()

    def __init__(self, filme_service, parent=None):
        super().__init__(parent)
        self.filme_service = filme_service
        self.filmes_exibidos = []
        self.operacao_thread = None
        self._tipo_operacao = None
        self._carregando = False

        self.label_titulo = QLabel('Filmes')
        self.label_titulo.setObjectName('tituloPagina')

        self.search_bar = SearchBar()

        self.combo_filtro = QComboBox()
        self.combo_filtro.addItem('Todos', None)
        self.combo_filtro.addItem('Disponiveis', True)
        self.combo_filtro.addItem('Indisponiveis', False)

        self.botao_novo = QPushButton('Novo Filme')
        self.botao_editar = QPushButton('Editar')
        self.botao_excluir = QPushButton('Excluir')

        self.label_operacao = QLabel('')
        self.label_operacao.setObjectName('statusOperacaoFilme')
        self.label_operacao.setVisible(False)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(
            ['ID', 'Titulo', 'Genero', 'Ano', 'Duracao', 'Status']
        )
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self._montar_layout()
        self._conectar_sinais()
        self.carregar_filmes()

    def carregar_filmes(self, filmes=None):
        self.filmes_exibidos = list(filmes) if filmes is not None else self._filtrar_filmes()
        self.tabela.setRowCount(len(self.filmes_exibidos))

        for linha, filme in enumerate(self.filmes_exibidos):
            itens = [
                QTableWidgetItem(str(filme.id)),
                QTableWidgetItem(filme.titulo),
                QTableWidgetItem(filme.genero),
                QTableWidgetItem(str(filme.ano)),
                QTableWidgetItem(f'{filme.duracao} min'),
                QTableWidgetItem(filme.status),
            ]
            for coluna, item in enumerate(itens):
                item.setData(Qt.ItemDataRole.UserRole, filme.id)
                self.tabela.setItem(linha, coluna, item)


    def pesquisar(self, texto):
        filmes = self._filtrar_filmes(texto)
        self.carregar_filmes(filmes)

    def abrir_cadastro(self):
        if self._operacao_bloqueada():
            return

        dialog = FilmeDialog(
            parent=self,
            permitir_editar_disponibilidade=False,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._executar_operacao(
                'cadastro',
                self.filme_service.adicionar_filme,
                **dialog.dados(),
            )

    def abrir_edicao(self):
        if self._operacao_bloqueada():
            return

        filme = self.filme_selecionado()
        if filme is None:
            QMessageBox.information(self, 'Selecione um filme', 'Selecione um filme.')
            return

        dialog = FilmeDialog(
            filme,
            self,
            permitir_editar_disponibilidade=False,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._executar_operacao(
                'edicao',
                self.filme_service.atualizar_filme,
                filme.id,
                **dialog.dados(),
            )

    def excluir_selecionado(self):
        if self._operacao_bloqueada():
            return

        filme = self.filme_selecionado()
        if filme is None:
            QMessageBox.information(self, 'Selecione um filme', 'Selecione um filme.')
            return

        resposta = QMessageBox.question(
            self,
            'Confirmar exclusao',
            'Deseja realmente excluir este filme?',
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        self._executar_operacao(
            'exclusao',
            self.filme_service.remover_filme,
            filme.id,
        )

    def filme_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self.filmes_exibidos):
            return None

        item = self.tabela.item(linha, 0)
        if item is None:
            return None
        return self.filme_service.obter_filme(int(item.data(Qt.ItemDataRole.UserRole)))

    def _montar_layout(self):
        area_busca = QHBoxLayout()
        area_busca.addWidget(self.search_bar)
        area_busca.addWidget(self.combo_filtro)

        area_botoes = QHBoxLayout()
        area_botoes.addWidget(self.botao_novo)
        area_botoes.addWidget(self.botao_editar)
        area_botoes.addWidget(self.botao_excluir)
        area_botoes.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self.label_titulo)
        layout.addLayout(area_busca)
        layout.addLayout(area_botoes)
        layout.addWidget(self.label_operacao)
        layout.addWidget(self.tabela)
        self.setLayout(layout)

    def _conectar_sinais(self):
        self.botao_novo.clicked.connect(self.abrir_cadastro)
        self.botao_editar.clicked.connect(self.abrir_edicao)
        self.botao_excluir.clicked.connect(self.excluir_selecionado)
        self.search_bar.search_changed.connect(self.pesquisar)
        self.combo_filtro.currentIndexChanged.connect(
            lambda: self.pesquisar(self.search_bar.texto())
        )
        self.tabela.itemDoubleClicked.connect(lambda _item: self.abrir_edicao())

    def _filtrar_filmes(self, texto=''):
        filmes = self.filme_service.buscar_filmes(texto)
        disponibilidade = self.combo_filtro.currentData()
        if disponibilidade is None:
            return filmes
        return [filme for filme in filmes if filme.disponivel == disponibilidade]

    def set_carregando(self, carregando):
        """Atualiza controles durante um carregamento remoto do acervo."""
        self._carregando = bool(carregando)
        if self._carregando:
            self.label_operacao.setText('Atualizando filmes...')
            self.label_operacao.setVisible(True)
        elif self.operacao_thread is None:
            self.label_operacao.clear()
            self.label_operacao.setVisible(False)
        self._atualizar_controles()

    def operacao_em_andamento(self):
        """Informa se cadastro, edicao ou exclusao ainda esta executando."""
        return (
            self.operacao_thread is not None
            and self.operacao_thread.isRunning()
        )

    def aguardar_operacao(self, timeout_ms):
        """Aguarda com limite uma operacao durante o fechamento da janela."""
        if not self.operacao_em_andamento():
            return True
        return self.operacao_thread.wait(timeout_ms)

    def _operacao_bloqueada(self):
        """Impede operacoes duplicadas ou iniciadas durante atualizacao."""
        if self._carregando or self.operacao_thread is not None:
            self.label_operacao.setText(
                'Aguarde a operacao de filmes em andamento.'
            )
            self.label_operacao.setVisible(True)
            return True
        return False

    def _executar_operacao(self, tipo, operacao, *args, **kwargs):
        """Cria e inicia um worker unico para uma chamada do service."""
        if self._operacao_bloqueada():
            return False

        self._tipo_operacao = tipo
        textos = {
            'cadastro': 'Cadastrando filme...',
            'edicao': 'Atualizando filme...',
            'exclusao': 'Excluindo filme...',
        }
        self.label_operacao.setText(textos[tipo])
        self.label_operacao.setVisible(True)
        self.operacao_thread = FilmeOperationThread(
            operacao,
            *args,
            parent=self,
            **kwargs,
        )
        self.operacao_thread.sucesso.connect(self._operacao_concluida)
        self.operacao_thread.erro.connect(self._operacao_falhou)
        self.operacao_thread.finished.connect(self._finalizar_operacao)
        self._atualizar_controles()
        self.operacao_thread.start()
        return True

    def _operacao_concluida(self, resultado):
        """Atualiza a tela somente depois da confirmacao da API."""
        tipo = self._tipo_operacao
        self.carregar_filmes()
        if tipo != 'exclusao' and resultado is not None:
            self._selecionar_filme(resultado.id)

        if tipo == 'cadastro':
            self.filme_cadastrado.emit()
            titulo = 'Filme cadastrado'
            mensagem = 'Filme cadastrado com sucesso.'
        elif tipo == 'edicao':
            self.filme_atualizado.emit()
            titulo = 'Filme atualizado'
            mensagem = 'Filme atualizado com sucesso.'
        else:
            self.filme_excluido.emit()
            titulo = 'Filme excluido'
            mensagem = 'Filme excluido com sucesso.'
        QMessageBox.information(self, titulo, mensagem)

    def _operacao_falhou(self, mensagem):
        """Apresenta falha segura sem descartar o acervo em memoria."""
        titulos = {
            'cadastro': 'Erro ao cadastrar',
            'edicao': 'Erro ao atualizar',
            'exclusao': 'Erro ao excluir',
        }
        QMessageBox.warning(
            self,
            titulos.get(self._tipo_operacao, 'Erro na operacao'),
            mensagem,
        )

    def _finalizar_operacao(self):
        """Restaura controles e libera o worker ja concluido."""
        thread = self.operacao_thread
        self.operacao_thread = None
        self._tipo_operacao = None
        if not self._carregando:
            self.label_operacao.clear()
            self.label_operacao.setVisible(False)
        self._atualizar_controles()
        if thread is not None:
            thread.deleteLater()

    def _atualizar_controles(self):
        """Evita envios duplicados enquanto ha comunicacao pendente."""
        habilitado = not self._carregando and self.operacao_thread is None
        self.botao_novo.setEnabled(habilitado)
        self.botao_editar.setEnabled(habilitado)
        self.botao_excluir.setEnabled(habilitado)

    def _selecionar_filme(self, filme_id):
        """Restaura a selecao apos cadastro ou edicao bem-sucedidos."""
        for linha, filme in enumerate(self.filmes_exibidos):
            if filme.id == filme_id:
                self.tabela.selectRow(linha)
                return
