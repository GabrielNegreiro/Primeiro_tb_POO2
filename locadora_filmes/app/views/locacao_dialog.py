from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class LocacaoDialog(QDialog):

    def __init__(self, filmes_disponiveis, locacao_service, parent=None, locacao=None):
        super().__init__(parent)
        self.locacao = locacao
        self.setWindowTitle('Editar Locacao' if locacao else 'Nova Locacao')

        self.filmes_disponiveis = filmes_disponiveis
        self.locacao_service = locacao_service
        self.locacao_criada = None

        self.combo_filme = QComboBox()
        for filme in self.filmes_disponiveis:
            self.combo_filme.addItem(filme.titulo, filme)

        self.campo_cliente = QLineEdit()
        self.campo_dias = QSpinBox()
        self.campo_dias.setRange(1, 30)
        self.campo_dias.setValue(7)

        if self.locacao is not None:
            self.campo_cliente.setText(self.locacao.cliente_nome)
            indice = self.combo_filme.findData(self.locacao.filme)
            if indice >= 0:
                self.combo_filme.setCurrentIndex(indice)
            if self.locacao.data_devolucao_prevista is not None:
                dias = (
                    self.locacao.data_devolucao_prevista - self.locacao.data_locacao
                ).days
                self.campo_dias.setValue(max(1, dias))

        layout_formulario = QFormLayout()
        layout_formulario.addRow('Filme:', self.combo_filme)
        layout_formulario.addRow('Cliente:', self.campo_cliente)
        layout_formulario.addRow('Dias de locacao:', self.campo_dias)

        botao_salvar = QPushButton(
            'Salvar Alteracoes' if locacao else 'Registrar Locacao'
        )
        botao_cancelar = QPushButton('Cancelar')
        botao_salvar.clicked.connect(self.salvar)
        botao_cancelar.clicked.connect(self.reject)

        layout_botoes = QHBoxLayout()
        layout_botoes.addWidget(botao_salvar)
        layout_botoes.addWidget(botao_cancelar)

        layout_principal = QVBoxLayout()
        layout_principal.addLayout(layout_formulario)
        layout_principal.addLayout(layout_botoes)
        self.setLayout(layout_principal)

    def salvar(self):
        if self.combo_filme.count() == 0:
            QMessageBox.warning(
                self, 'Sem filmes', 'Nao ha filmes disponiveis para locacao.'
            )
            return

        cliente_nome = self.campo_cliente.text().strip()
        if not cliente_nome:
            QMessageBox.warning(
                self, 'Campo obrigatorio', 'Informe o nome do cliente.'
            )
            return

        filme = self.combo_filme.currentData()
        dias = self.campo_dias.value()

        try:
            if self.locacao is None:
                self.locacao_criada = self.locacao_service.criar_locacao(
                    filme, cliente_nome, dias_previstos=dias
                )
            else:
                self.locacao_criada = self.locacao_service.atualizar_locacao(
                    self.locacao, filme, cliente_nome, dias_previstos=dias
                )
        except ValueError as erro:
            QMessageBox.critical(self, 'Erro ao salvar locacao', str(erro))
            return

        self.accept()
