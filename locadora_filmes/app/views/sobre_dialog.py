from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class SobreDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Sobre')

        texto = (
            '<h3>Locadora de Filmes</h3>'
            '<p>Trabalho 1 - Programação Orientada a Objetos II</p>'
            '<p>Universidade Federal do Piauí (UFPI)</p>'
            '<p><b>Integrantes:</b><br>'
            'Nilson Bruno<br>'
            'Gabriel Negreiro</p>'
        )

        label_info = QLabel(texto)
        label_info.setWordWrap(True)

        botao_fechar = QPushButton('Fechar')
        botao_fechar.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(label_info)
        layout.addWidget(botao_fechar)
        self.setLayout(layout)