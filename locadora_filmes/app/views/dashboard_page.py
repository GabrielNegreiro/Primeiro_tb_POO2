from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

class DashboardPage(QWidget):

    def __init__(self, locacao_service, filme_service, parent=None):
        super().__init__(parent)

        self.locacao_service = locacao_service
        self.filme_service = filme_service

        self.label_titulo = QLabel('Resumo da Locadora')
        self.label_ativas = QLabel()
        self.label_atrasadas = QLabel()
        self.label_disponiveis = QLabel()

        botao_atualizar = QPushButton('Atualizar')
        botao_atualizar.clicked.connect(self.atualizar_resumo)

        layout = QVBoxLayout()
        layout.addWidget(self.label_titulo)
        layout.addWidget(self.label_ativas)
        layout.addWidget(self.label_atrasadas)
        layout.addWidget(self.label_disponiveis)
        layout.addWidget(botao_atualizar)
        self.setLayout(layout)

        self.atualizar_resumo()

    def atualizar_resumo(self):
        ativas = self.locacao_service.listar_ativas()
        atrasadas = self.locacao_service.listar_atrasadas()
        disponiveis = self.filme_service.listar_disponiveis()

        self.label_ativas.setText(f'Locações em aberto: {len(ativas)}')
        self.label_atrasadas.setText(f'Locações atrasadas: {len(atrasadas)}')
        self.label_disponiveis.setText(f'Filmes disponíveis: {len(disponiveis)}')