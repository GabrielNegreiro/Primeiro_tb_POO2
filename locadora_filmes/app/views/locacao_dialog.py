from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QPushButton, QMessageBox
)


class LocacaoDialog(QDialog):

    def __init__(self, filmes_disponiveis, locacao_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Nova Locação')

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

        layout_formulario = QFormLayout()
        layout_formulario.addRow('Filme:', self.combo_filme)
        layout_formulario.addRow('Cliente:', self.campo_cliente)
        layout_formulario.addRow('Dias de locação:', self.campo_dias)

        botao_salvar = QPushButton('Registrar Locação')
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
            QMessageBox.warning(self, 'Sem filmes', 'Não há filmes disponíveis para locação.')
            return

        cliente_nome = self.campo_cliente.text().strip()
        if not cliente_nome:
            QMessageBox.warning(self, 'Campo obrigatório', 'Informe o nome do cliente.')
            return

        filme = self.combo_filme.currentData()
        dias = self.campo_dias.value()

        try:
            self.locacao_criada = self.locacao_service.criar_locacao(
                filme, cliente_nome, dias_previstos=dias
            )
        except ValueError as erro:
            QMessageBox.critical(self, 'Erro ao registrar locação', str(erro))
            return

        self.accept()