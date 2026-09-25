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


class FilmesPage(QWidget):
    filme_cadastrado = Signal()
    filme_atualizado = Signal()
    filme_excluido = Signal()

    def __init__(self, filme_service, parent=None):
        super().__init__(parent)
        self.filme_service = filme_service
        self.filmes_exibidos = []

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
        dialog = FilmeDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.filme_service.adicionar_filme(**dialog.dados())
            self.carregar_filmes()
            self.filme_cadastrado.emit()
            QMessageBox.information(self, 'Filme cadastrado', 'Filme cadastrado com sucesso.')

    def abrir_edicao(self):
        filme = self.filme_selecionado()
        if filme is None:
            QMessageBox.information(self, 'Selecione um filme', 'Selecione um filme.')
            return

        dialog = FilmeDialog(filme, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.filme_service.atualizar_filme(filme.id, **dialog.dados())
            self.carregar_filmes()
            self.filme_atualizado.emit()
            QMessageBox.information(self, 'Filme atualizado', 'Filme atualizado com sucesso.')

    def excluir_selecionado(self):
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

        try:
            self.filme_service.remover_filme(filme.id)
        except ValueError as erro:
            QMessageBox.warning(self, 'Erro ao excluir', str(erro))
            return

        self.carregar_filmes()
        self.filme_excluido.emit()
        QMessageBox.information(self, 'Filme excluido', 'Filme excluido com sucesso.')

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
