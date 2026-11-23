from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.locacao_api import titulo_do_filme
from app.views.exportar_thread import ExportarRelatorioThread
from app.views.locacao_dialog import LocacaoDialog
from app.workers.locacao_operation_thread import LocacaoOperationThread


class LocacoesPage(QWidget):

    locacoes_alteradas = Signal()

    def __init__(self, locacao_service, filme_service, parent=None):
        super().__init__(parent)

        self.locacao_service = locacao_service
        self.filme_service = filme_service
        # Modo HTTP: operacoes de rede em workers e selecao pelo ID da locacao.
        self.assincrono = getattr(locacao_service, 'assincrono', False) is True
        self.thread_exportacao = None
        self.operacao_thread = None
        self._tipo_operacao = None
        self._carregando = False
        self.modo_integracao_pendente = False
        self.mensagem_integracao_pendente = ''

        self.label_integracao = QLabel('')
        self.label_integracao.setWordWrap(True)
        self.label_integracao.setVisible(False)

        self.label_operacao = QLabel('')
        self.label_operacao.setObjectName('statusOperacaoLocacao')
        self.label_operacao.setVisible(False)

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
        layout_principal.addWidget(self.label_integracao)
        layout_principal.addWidget(self.label_operacao)
        layout_principal.addWidget(self.tabela)
        layout_principal.addLayout(layout_botoes)
        self.setLayout(layout_principal)

        self.atualizar_tabela()

    # --- tabela e selecao ------------------------------------------------

    def atualizar_tabela(self):
        selecionado = self._id_selecionado()
        locacoes = self.locacao_service.listar_todas()
        self.tabela.setRowCount(len(locacoes))

        for linha, locacao in enumerate(locacoes):
            identificador = getattr(locacao, 'id', None)
            textos = [
                titulo_do_filme(locacao),
                locacao.cliente_nome,
                str(locacao.data_locacao),
                str(locacao.data_devolucao_prevista),
                locacao.status,
            ]
            for coluna, texto in enumerate(textos):
                item = QTableWidgetItem(texto)
                item.setData(Qt.ItemDataRole.UserRole, identificador)
                self.tabela.setItem(linha, coluna, item)

        if selecionado is not None:
            self._selecionar_por_id(selecionado)

    def _id_selecionado(self):
        if not self.assincrono:
            return None
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        item = self.tabela.item(linha, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selecionar_por_id(self, locacao_id):
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == locacao_id:
                self.tabela.selectRow(linha)
                return

    def locacao_selecionada(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            return None
        if self.assincrono:
            identificador = self._id_selecionado()
            if identificador is None:
                return None
            return self.locacao_service.obter_locacao(identificador)
        return self.locacao_service.listar_todas()[linha]

    def _avisar_sem_selecao(self):
        QMessageBox.information(
            self,
            'Nenhuma locacao selecionada',
            'Selecione uma locacao na tabela primeiro.',
        )

    # --- acoes -----------------------------------------------------------

    def abrir_nova_locacao(self):
        if self._bloquear_operacao_pendente() or self._operacao_bloqueada():
            return
        filmes_disponiveis = self.filme_service.listar_disponiveis()

        if not filmes_disponiveis:
            QMessageBox.information(
                self,
                'Sem filmes disponiveis',
                'Nao ha filmes disponiveis para locacao no momento.',
            )
            return

        dialog = LocacaoDialog(filmes_disponiveis, self.locacao_service, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if self.assincrono:
            dados = dialog.dados()
            self._executar_operacao(
                'cadastro',
                self.locacao_service.criar_locacao,
                dados['filme'],
                dados['cliente_nome'],
                dias_previstos=dados['dias'],
            )
            return
        self.atualizar_tabela()
        self.locacoes_alteradas.emit()

    def abrir_edicao(self):
        if self._bloquear_operacao_pendente() or self._operacao_bloqueada():
            return
        locacao = self.locacao_selecionada()
        if locacao is None:
            self._avisar_sem_selecao()
            return
        if locacao.data_devolucao_real is not None:
            QMessageBox.information(
                self,
                'Locacao devolvida',
                'Somente locacoes em aberto podem ser editadas.',
            )
            return

        filme_atual = locacao.filme
        if filme_atual is None:
            QMessageBox.information(
                self,
                'Filme nao carregado',
                'O filme desta locacao ainda nao foi carregado. '
                'Atualize os dados e tente novamente.',
            )
            return

        filmes = [filme_atual]
        filmes.extend(
            filme
            for filme in self.filme_service.listar_disponiveis()
            if filme.id != filme_atual.id
        )
        dialog = LocacaoDialog(
            filmes,
            self.locacao_service,
            self,
            locacao=locacao,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if self.assincrono:
            dados = dialog.dados()
            self._executar_operacao(
                'edicao',
                self.locacao_service.atualizar_locacao,
                locacao.id,
                dados['filme'],
                dados['cliente_nome'],
                dados['dias'],
            )
            return
        self.atualizar_tabela()
        self.locacoes_alteradas.emit()

    def devolver_selecionada(self):
        if self._bloquear_operacao_pendente() or self._operacao_bloqueada():
            return
        locacao = self.locacao_selecionada()
        if locacao is None:
            self._avisar_sem_selecao()
            return

        if self.assincrono:
            if locacao.data_devolucao_real is not None:
                QMessageBox.warning(
                    self, 'Erro ao devolver', 'Locacao ja foi devolvida.'
                )
                return
            self._executar_operacao(
                'devolucao', self.locacao_service.devolver_locacao, locacao.id
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
        if self._bloquear_operacao_pendente() or self._operacao_bloqueada():
            return
        locacao = self.locacao_selecionada()
        if locacao is None:
            self._avisar_sem_selecao()
            return

        if self.assincrono and locacao.data_devolucao_real is None:
            QMessageBox.warning(
                self,
                'Erro ao excluir',
                'Devolva a locacao antes de exclui-la.',
            )
            return

        resposta = QMessageBox.question(
            self,
            'Confirmar exclusao',
            f'Excluir a locacao de {locacao.cliente_nome} '
            f'({titulo_do_filme(locacao)})?',
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        if self.assincrono:
            self._executar_operacao(
                'exclusao',
                self.locacao_service.excluir_locacao,
                locacao.id,
                atualizar=False,
            )
            return

        try:
            self.locacao_service.excluir_locacao(locacao)
        except ValueError as erro:
            QMessageBox.warning(self, 'Erro ao excluir', str(erro))
            return

        self.atualizar_tabela()
        self.locacoes_alteradas.emit()

    # --- operacoes HTTP assincronas --------------------------------------

    def set_carregando(self, carregando):
        """Atualiza controles durante o carregamento remoto das locacoes."""
        self._carregando = bool(carregando)
        if self._carregando:
            self.label_operacao.setText('Atualizando locacoes...')
            self.label_operacao.setVisible(True)
        elif self.operacao_thread is None:
            self.label_operacao.clear()
            self.label_operacao.setVisible(False)
        self._atualizar_controles()

    def operacao_em_andamento(self):
        """Informa se cadastro, edicao, devolucao ou exclusao esta rodando."""
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
                'Aguarde a operacao de locacoes em andamento.'
            )
            self.label_operacao.setVisible(True)
            return True
        return False

    def _executar_operacao(self, tipo, operacao, *args, atualizar=True, **kwargs):
        """Cria e inicia um worker unico para uma chamada do servico."""
        if self._operacao_bloqueada():
            return False

        self._tipo_operacao = tipo
        textos = {
            'cadastro': 'Registrando locacao...',
            'edicao': 'Atualizando locacao...',
            'devolucao': 'Registrando devolucao...',
            'exclusao': 'Excluindo locacao...',
        }
        self.label_operacao.setText(textos[tipo])
        self.label_operacao.setVisible(True)
        atualizar_filmes = (
            self.locacao_service.atualizar_filmes if atualizar else None
        )
        self.operacao_thread = LocacaoOperationThread(
            operacao,
            *args,
            atualizar_filmes=atualizar_filmes,
            parent=self,
            **kwargs,
        )
        self.operacao_thread.sucesso.connect(self._operacao_concluida)
        self.operacao_thread.sucesso_sem_atualizacao.connect(
            self._operacao_concluida_sem_atualizacao
        )
        self.operacao_thread.erro.connect(self._operacao_falhou)
        self.operacao_thread.finished.connect(self._finalizar_operacao)
        self._atualizar_controles()
        self.operacao_thread.start()
        return True

    def _depois_da_operacao(self, tipo, resultado):
        self.atualizar_tabela()
        if tipo != 'exclusao' and resultado is not None:
            self._selecionar_por_id(resultado.id)
        self.locacoes_alteradas.emit()

    def _operacao_concluida(self, resultado):
        """Atualiza a tela somente depois da confirmacao da API."""
        tipo = self._tipo_operacao
        self._depois_da_operacao(tipo, resultado)
        mensagens = {
            'cadastro': ('Locacao registrada', 'Locacao registrada com sucesso.'),
            'edicao': ('Locacao atualizada', 'Locacao atualizada com sucesso.'),
            'devolucao': ('Locacao devolvida', 'Devolucao registrada com sucesso.'),
            'exclusao': ('Locacao excluida', 'Locacao excluida com sucesso.'),
        }
        titulo, mensagem = mensagens[tipo]
        QMessageBox.information(self, titulo, mensagem)

    def _operacao_concluida_sem_atualizacao(self, resultado, motivo):
        """A API confirmou a operacao, mas o acervo nao foi recarregado."""
        tipo = self._tipo_operacao
        self._depois_da_operacao(tipo, resultado)
        QMessageBox.warning(
            self,
            'Operacao concluida',
            'A operacao foi concluida no servidor, mas nao foi possivel '
            'atualizar o acervo de filmes.\n\n'
            f'{motivo}\n\nUse Atualizar para recarregar os dados.',
        )

    def _operacao_falhou(self, mensagem):
        """Apresenta falha segura sem alterar o cache nem simular sucesso."""
        titulos = {
            'cadastro': 'Erro ao registrar locacao',
            'edicao': 'Erro ao atualizar locacao',
            'devolucao': 'Erro ao devolver',
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
        if self.modo_integracao_pendente:
            return
        habilitado = not self._carregando and self.operacao_thread is None
        for botao in (
            self.botao_nova,
            self.botao_editar,
            self.botao_devolver,
            self.botao_excluir,
        ):
            botao.setEnabled(habilitado)

    # --- exportacao ------------------------------------------------------

    def exportar_relatorio(self):
        if self.exportacao_em_andamento():
            return

        if self.assincrono and getattr(
            self.locacao_service, 'carregado', True
        ) is False:
            QMessageBox.information(
                self,
                'Dados nao carregados',
                'As locacoes ainda nao foram carregadas da API. '
                'Use Atualizar e tente novamente.',
            )
            return

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
        self.thread_exportacao.finished.connect(self._finalizar_exportacao)
        self.thread_exportacao.start()

    def exportacao_em_andamento(self):
        return (
            self.thread_exportacao is not None
            and self.thread_exportacao.isRunning()
        )

    def aguardar_exportacao(self, timeout_ms):
        if not self.exportacao_em_andamento():
            return True
        return self.thread_exportacao.wait(timeout_ms)

    def _finalizar_exportacao(self):
        thread = self.thread_exportacao
        self.thread_exportacao = None
        self.botao_exportar.setEnabled(True)
        if thread is not None:
            thread.deleteLater()

    def exportacao_concluida(self, caminho):
        QMessageBox.information(
            self, 'Relatorio exportado', f'Relatorio salvo em:\n{caminho}'
        )

    def exportacao_falhou(self, mensagem):
        QMessageBox.warning(self, 'Erro ao exportar', mensagem)

    # --- modo pendente (somente quando nao ha servico HTTP) --------------

    def ativar_modo_integracao_pendente(self, mensagem):
        """Preserva a tela, mas bloqueia operacoes locais incompatíveis."""
        self.modo_integracao_pendente = True
        self.mensagem_integracao_pendente = mensagem
        self.label_integracao.setText(mensagem)
        self.label_integracao.setVisible(True)
        for botao in (
            self.botao_nova,
            self.botao_editar,
            self.botao_devolver,
            self.botao_excluir,
        ):
            botao.setEnabled(False)
            botao.setToolTip(mensagem)

    def _bloquear_operacao_pendente(self):
        """Explica por que locacoes locais nao podem alterar filmes da API."""
        if not self.modo_integracao_pendente:
            return False
        QMessageBox.information(
            self,
            'Integracao de locacoes pendente',
            self.mensagem_integracao_pendente,
        )
        return True