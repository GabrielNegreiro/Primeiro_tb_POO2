from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.views.exportar_thread import ExportarRelatorioThread
from app.views.locacao_dialog import LocacaoDialog


class LocacoesPage(QWidget):

    locacoes_alteradas = Signal()

    def __init__(self, locacao_service, filme_service, parent=None):
        super().__init__(parent)

        self.locacao_service = locacao_service
        self.filme_service = filme_service
        self.thread_exportacao = None

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(5)
        self.tabela.setHorizontalHeaderLabels(
            ['Filme', 'Cliente', 'Locacao', 'Prevista', 'Status']
        )
        self.tabela.cellDoubleClicked.connect(
            lambda _linha, _coluna: self.abrir_edicao()
        )

        self.botao_nova = QPushButton('Registrar Nova Locacao')
        self.botao_editar = QPushButton('Editar Selecionada')
        self.botao_devolver = QPushButton('Devolver Selecionada')
        self.botao_excluir = QPushButton('Excluir Selecionada')
        self.botao_exportar = QPushButton('Exportar Relatorio')
        self.botao_nova.clicked.connect(self.abrir_nova_locacao)
        self.botao_editar.clicked.connect(self.abrir_edicao)
        self.botao_devolver.clicked.connect(self.devolver_selecionada)
        self.botao_excluir.clicked.connect(self.excluir_selecionada)
        self.botao_exportar.clicked.connect(self.exportar_relatorio)

        layout_botoes = QHBoxLayout()
        layout_botoes.addWidget(self.botao_nova)
        layout_botoes.addWidget(self.botao_editar)
        layout_botoes.addWidget(self.botao_devolver)
        layout_botoes.addWidget(self.botao_excluir)
        layout_botoes.addWidget(self.botao_exportar)

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
            self.tabela.setItem(
                linha, 2, QTableWidgetItem(str(locacao.data_locacao))
            )
            self.tabela.setItem(
                linha, 3, QTableWidgetItem(str(locacao.data_devolucao_prevista))
            )
            self.tabela.setItem(linha, 4, QTableWidgetItem(locacao.status))

    def abrir_nova_locacao(self):
        filmes_disponiveis = self.filme_service.listar_disponiveis()

        if not filmes_disponiveis:
            QMessageBox.information(
                self,
                'Sem filmes disponiveis',
                'Nao ha filmes disponiveis para locacao no momento.',
            )
            return

        dialog = LocacaoDialog(filmes_disponiveis, self.locacao_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.atualizar_tabela()
            self.locacoes_alteradas.emit()

    def abrir_edicao(self):
        locacao = self.locacao_selecionada()
        if locacao is None:
            QMessageBox.information(
                self,
                'Nenhuma locacao selecionada',
                'Selecione uma locacao na tabela primeiro.',
            )
            return
        if locacao.data_devolucao_real is not None:
            QMessageBox.information(
                self,
                'Locacao devolvida',
                'Somente locacoes em aberto podem ser editadas.',
            )
            return

        filmes = [locacao.filme]
        filmes.extend(
            filme
            for filme in self.filme_service.listar_disponiveis()
            if filme is not locacao.filme
        )
        dialog = LocacaoDialog(
            filmes,
            self.locacao_service,
            self,
            locacao=locacao,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.atualizar_tabela()
            self.locacoes_alteradas.emit()

    def locacao_selecionada(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        return self.locacao_service.listar_todas()[linha]

    def devolver_selecionada(self):
        locacao = self.locacao_selecionada()
        if locacao is None:
            QMessageBox.information(
                self,
                'Nenhuma locacao selecionada',
                'Selecione uma locacao na tabela primeiro.',
            )
            return

        try:
            self.locacao_service.devolver_locacao(locacao)
        except ValueError as erro:
            QMessageBox.warning(self, 'Erro ao devolver', str(erro))
            return

        self.atualizar_tabela()
        self.locacoes_alteradas.emit()

    def excluir_selecionada(self):
        locacao = self.locacao_selecionada()
        if locacao is None:
            QMessageBox.information(
                self,
                'Nenhuma locacao selecionada',
                'Selecione uma locacao na tabela primeiro.',
            )
            return

        resposta = QMessageBox.question(
            self,
            'Confirmar exclusao',
            f'Excluir a locacao de {locacao.cliente_nome} '
            f'({locacao.filme.titulo})?',
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            self.locacao_service.excluir_locacao(locacao)
        except ValueError as erro:
            QMessageBox.warning(self, 'Erro ao excluir', str(erro))
            return

        self.atualizar_tabela()
        self.locacoes_alteradas.emit()

    def exportar_relatorio(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            'Exportar relatorio',
            'relatorio_locacoes.txt',
            'Arquivo de texto (*.txt)',
        )
        if not caminho:
            return

        self.botao_exportar.setEnabled(False)
        self.thread_exportacao = ExportarRelatorioThread(
            self.locacao_service.listar_todas(), caminho, self
        )
        self.thread_exportacao.concluido.connect(self.exportacao_concluida)
        self.thread_exportacao.falhou.connect(self.exportacao_falhou)
        self.thread_exportacao.finished.connect(
            lambda: self.botao_exportar.setEnabled(True)
        )
        self.thread_exportacao.start()

    def exportacao_concluida(self, caminho):
        QMessageBox.information(
            self, 'Relatorio exportado', f'Relatorio salvo em:\n{caminho}'
        )

    def exportacao_falhou(self, mensagem):
        QMessageBox.warning(self, 'Erro ao exportar', mensagem)