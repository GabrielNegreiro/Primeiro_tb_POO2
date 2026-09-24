from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QMessageBox, QDialog
)

from app.views.locacao_dialog import LocacaoDialog

class LocacoesPage(QWidget):

    def __init__(self, locacao_service, filme_service, parent=None):
        super().__init__(parent)

        self.locacao_service = locacao_service
        self.filme_service = filme_service

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(
            ['Filme', 'Cliente', 'Locação', 'Prevista', 'Status']
        )

        botao_nova = QPushButton('Registrar Nova Locação')
        botao_devolver = QPushButton('Devolver Selecionada')
        botao_nova.clicked.connect(self.abrir_nova_locacao)
        botao_devolver.clicked.connect(self.devolver_selecionada)

        layout_botoes = QHBoxLayout()
        layout_botoes.addWidget(botao_nova)
        layout_botoes.addWidget(botao_devolver)

        layout_principal = QVBoxLayout()
        layout_principal.addWidget(self.tabela)
        layout_principal.addLayout(layout_botoes)
        self.setLayout(layout_principal)

        self.atualizar_tabela()

    def atualizar_tabela(self):
        locacoes = self.locacao_service.listar_todas()
        self.tabela.setRowCount(len(locacoes))

        for linha, locacao in enumerate(locacoes):
            self.tabela.setItem(linha, 0, QTableWidgetItem(locacao.filme.titulo))
            self.tabela.setItem(linha, 1, QTableWidgetItem(locacao.cliente_nome))
            self.tabela.setItem(linha, 2, QTableWidgetItem(str(locacao.data_locacao)))
            self.tabela.setItem(linha, 3, QTableWidgetItem(str(locacao.data_devolucao_prevista)))
            self.tabela.setItem(linha, 4, QTableWidgetItem(locacao.status))

    def abrir_nova_locacao(self):
        filmes_disponiveis = self.filme_service.listar_disponiveis()

        if not filmes_disponiveis:
            QMessageBox.information(self, 'Sem filmes disponíveis',
                                     'Não há filmes disponíveis para locação no momento.')
            return

        dialog = LocacaoDialog(filmes_disponiveis, self.locacao_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.atualizar_tabela()

    def devolver_selecionada(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(self, 'Nenhuma locação selecionada',
                                     'Selecione uma locação na tabela primeiro.')
            return

        locacao = self.locacao_service.listar_todas()[linha]

        try:
            self.locacao_service.devolver_locacao(locacao)
        except ValueError as erro:
            QMessageBox.warning(self, 'Erro ao devolver', str(erro))
            return

        self.atualizar_tabela()
        