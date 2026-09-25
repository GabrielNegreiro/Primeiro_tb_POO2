from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class FilmeCard(QFrame):
    def __init__(self, filme, parent=None):
        super().__init__(parent)
        self.filme = filme

        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.label_titulo = QLabel(filme.titulo)
        self.label_genero = QLabel(f'{filme.genero} - {filme.ano}')
        self.label_status = QLabel(f'Status: {filme.status}')

        layout = QVBoxLayout()
        layout.addWidget(self.label_titulo)
        layout.addWidget(self.label_genero)
        layout.addWidget(self.label_status)
        self.setLayout(layout)
