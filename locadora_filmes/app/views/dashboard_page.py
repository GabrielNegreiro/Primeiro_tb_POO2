from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):

    def __init__(self, locacao_service, filme_service, parent=None):
        super().__init__(parent)

        self.locacao_service = locacao_service
        self.filme_service = filme_service

        self.label_titulo = QLabel('Dashboard')
        self.label_titulo.setObjectName('tituloDashboard')

        self.label_ativas = QLabel('0')
        self.label_atrasadas = QLabel('0')
        self.label_disponiveis = QLabel('0')

        self.botao_atualizar = QPushButton('Atualizar')
        self.botao_atualizar.setObjectName('botaoAtualizar')
        self.botao_atualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_atualizar.clicked.connect(self.atualizar_resumo)

        self.tabela_recentes = QTableWidget()
        self.tabela_recentes.setObjectName('tabelaRecentes')
        self.tabela_recentes.setColumnCount(4)
        self.tabela_recentes.setHorizontalHeaderLabels(
            ['Filme', 'Cliente', 'Devolução prevista', 'Status']
        )
        self.tabela_recentes.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tabela_recentes.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.tabela_recentes.setAlternatingRowColors(True)
        self.tabela_recentes.verticalHeader().setVisible(False)
        self.tabela_recentes.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tabela_recentes.setMinimumHeight(190)

        self.label_sem_movimentacoes = QLabel(
            'Nenhuma locação registrada até o momento.'
        )
        self.label_sem_movimentacoes.setObjectName('estadoVazio')
        self.label_sem_movimentacoes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_sem_movimentacoes.setMinimumHeight(150)

        self._montar_layout()
        self._aplicar_estilo()
        self.atualizar_resumo()

    def _montar_layout(self):
        quadro_cabecalho = QFrame()
        quadro_cabecalho.setObjectName('cabecalhoDashboard')
        cabecalho = QHBoxLayout(quadro_cabecalho)
        cabecalho.setContentsMargins(18, 14, 18, 14)
        cabecalho.addWidget(self.label_titulo)
        cabecalho.addStretch()
        cabecalho.addWidget(self.botao_atualizar)

        indicadores = QHBoxLayout()
        indicadores.setSpacing(12)
        indicadores.addWidget(
            self._criar_indicador(
                'Locações em aberto', self.label_ativas, 'indicadorAberto'
            )
        )
        indicadores.addWidget(
            self._criar_indicador(
                'Locações atrasadas', self.label_atrasadas, 'indicadorAtrasado'
            )
        )
        indicadores.addWidget(
            self._criar_indicador(
                'Filmes disponíveis', self.label_disponiveis, 'indicadorDisponivel'
            )
        )

        titulo_recentes = QLabel('Movimentações recentes')
        titulo_recentes.setObjectName('tituloSecao')

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(18)
        layout.addWidget(quadro_cabecalho)
        layout.addLayout(indicadores)
        layout.addSpacing(4)
        layout.addWidget(titulo_recentes)
        layout.addWidget(self.tabela_recentes)
        layout.addWidget(self.label_sem_movimentacoes)
        layout.addStretch()
        self.setLayout(layout)

    def _criar_indicador(self, titulo, label_valor, nome):
        quadro = QFrame()
        quadro.setObjectName(nome)
        quadro.setProperty('tipo', 'indicador')
        quadro.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        quadro.setMinimumHeight(108)

        label_titulo = QLabel(titulo)
        label_titulo.setProperty('tipo', 'rotuloIndicador')
        label_valor.setProperty('tipo', 'valorIndicador')

        layout = QVBoxLayout(quadro)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(4)
        layout.addWidget(label_titulo)
        layout.addWidget(label_valor)
        return quadro

    def _aplicar_estilo(self):
        self.setStyleSheet(
            """
            DashboardPage {
                background: #f6f7f9;
            }
            QFrame#cabecalhoDashboard {
                background: #ffffff;
                border: 1px solid #e4e7ec;
                border-radius: 12px;
            }
            QLabel#tituloDashboard {
                background: #ffffff;
                color: #2563eb;
                font-size: 24px;
                font-weight: 700;
            }
            QPushButton#botaoAtualizar {
                background: #ffffff;
                color: #344054;
                border: 1px solid #d0d5dd;
                border-radius: 5px;
                padding: 7px 14px;
                font-weight: 600;
            }
            QPushButton#botaoAtualizar:hover {
                background: #f2f4f7;
                border-color: #98a2b3;
            }
            QFrame[tipo="indicador"] {
                background: #ffffff;
                border: 1px solid #e4e7ec;
                border-radius: 6px;
                border-left-width: 4px;
            }
            QFrame#indicadorAberto {
                border-left-color: #2e6fbb;
            }
            QFrame#indicadorAtrasado {
                border-left-color: #c2413b;
            }
            QFrame#indicadorDisponivel {
                border-left-color: #27835b;
            }
            QLabel[tipo="rotuloIndicador"] {
                color: #667085;
                font-size: 13px;
            }
            QLabel[tipo="valorIndicador"] {
                color: #172033;
                font-size: 29px;
                font-weight: 700;
            }
            QLabel#tituloSecao {
                color: #172033;
                font-size: 16px;
                font-weight: 700;
            }
            QTableWidget#tabelaRecentes {
                background: #ffffff;
                alternate-background-color: #fafafa;
                border: 1px solid #e4e7ec;
                border-radius: 5px;
                color: #344054;
                gridline-color: #eaecf0;
                selection-background-color: #e7f0fa;
                selection-color: #172033;
            }
            QTableWidget#tabelaRecentes::item {
                padding: 7px;
            }
            QHeaderView::section {
                background: #f2f4f7;
                color: #475467;
                border: none;
                border-bottom: 1px solid #d0d5dd;
                padding: 8px;
                font-weight: 600;
            }
            QLabel#estadoVazio {
                background: #ffffff;
                color: #667085;
                border: 1px solid #e4e7ec;
                border-radius: 5px;
            }
            """
        )

    def atualizar_resumo(self):
        ativas = self.locacao_service.listar_ativas()
        atrasadas = self.locacao_service.listar_atrasadas()
        disponiveis = self.filme_service.listar_disponiveis()

        self.label_ativas.setText(str(len(ativas)))
        self.label_atrasadas.setText(str(len(atrasadas)))
        self.label_disponiveis.setText(str(len(disponiveis)))
        self._atualizar_recentes()

    def _atualizar_recentes(self):
        locacoes = self.locacao_service.listar_todas()[-5:]
        locacoes.reverse()

        possui_locacoes = bool(locacoes)
        self.tabela_recentes.setVisible(possui_locacoes)
        self.label_sem_movimentacoes.setVisible(not possui_locacoes)
        self.tabela_recentes.setRowCount(len(locacoes))

        for linha, locacao in enumerate(locacoes):
            status = 'Atrasada' if locacao.atrasada else locacao.status
            itens = [
                QTableWidgetItem(locacao.filme.titulo),
                QTableWidgetItem(locacao.cliente_nome),
                QTableWidgetItem(str(locacao.data_devolucao_prevista)),
                QTableWidgetItem(status),
            ]
            if locacao.atrasada:
                itens[-1].setForeground(QColor('#b42318'))
            elif locacao.status == 'Em aberto':
                itens[-1].setForeground(QColor('#175cd3'))
            else:
                itens[-1].setForeground(QColor('#067647'))

            for coluna, item in enumerate(itens):
                self.tabela_recentes.setItem(linha, coluna, item)
