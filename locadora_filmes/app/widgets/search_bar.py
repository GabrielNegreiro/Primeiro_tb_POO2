from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBar(QWidget):
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.campo_pesquisa = QLineEdit()
        self.campo_pesquisa.setPlaceholderText('Pesquisar filme...')

        self.botao_limpar = QPushButton('Limpar')

        layout = QHBoxLayout()
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.botao_limpar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # SIGNAL/SLOT: pesquisa enquanto o texto e alterado.
        self.campo_pesquisa.textChanged.connect(self.search_changed.emit)
        self.botao_limpar.clicked.connect(self.limpar)

    def texto(self):
        return self.campo_pesquisa.text()

    def limpar(self):
        self.campo_pesquisa.clear()
