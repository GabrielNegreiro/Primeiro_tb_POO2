from datetime import date

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


class FilmeDialog(QDialog):
    GENEROS = [
        'Acao',
        'Animacao',
        'Aventura',
        'Comedia',
        'Drama',
        'Ficcao',
        'Romance',
        'Suspense',
        'Terror',
    ]

    def __init__(self, filme=None, parent=None):
        super().__init__(parent)
        self.filme = filme
        self.setWindowTitle('Editar Filme' if filme else 'Novo Filme')

        self.campo_titulo = QLineEdit()

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(self.GENEROS)

        self.campo_ano = QSpinBox()
        self.campo_ano.setRange(1888, date.today().year + 1)
        self.campo_ano.setValue(date.today().year)

        self.campo_duracao = QSpinBox()
        self.campo_duracao.setRange(1, 600)
        self.campo_duracao.setSuffix(' min')

        self.combo_status = QComboBox()
        self.combo_status.addItem('Disponivel', True)
        self.combo_status.addItem('Indisponivel', False)

        formulario = QFormLayout()
        formulario.addRow('Titulo:', self.campo_titulo)
        formulario.addRow('Genero:', self.combo_genero)
        formulario.addRow('Ano:', self.campo_ano)
        formulario.addRow('Duracao:', self.campo_duracao)
        formulario.addRow('Status:', self.combo_status)

        self.botao_salvar = QPushButton('Salvar')
        self.botao_cancelar = QPushButton('Cancelar')
        self.botao_salvar.clicked.connect(self.salvar)
        self.botao_cancelar.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.botao_salvar)
        botoes.addWidget(self.botao_cancelar)

        layout = QVBoxLayout()
        layout.addLayout(formulario)
        layout.addLayout(botoes)
        self.setLayout(layout)

        if filme is not None:
            self._preencher_campos(filme)

    def dados(self):
        return {
            'titulo': self.campo_titulo.text().strip(),
            'genero': self.combo_genero.currentText(),
            'ano': self.campo_ano.value(),
            'duracao': self.campo_duracao.value(),
            'disponivel': self.combo_status.currentData(),
        }

    def salvar(self):
        if not self.validar():
            return
        self.accept()

    def validar(self):
        dados = self.dados()

        if not dados['titulo']:
            QMessageBox.warning(self, 'Campo obrigatorio', 'Informe o titulo do filme.')
            return False
        if not dados['genero']:
            QMessageBox.warning(self, 'Campo obrigatorio', 'Informe o genero do filme.')
            return False
        if dados['ano'] < 1888:
            QMessageBox.warning(self, 'Ano invalido', 'Informe um ano valido.')
            return False
        if dados['duracao'] <= 0:
            QMessageBox.warning(self, 'Duracao invalida', 'Informe uma duracao maior que zero.')
            return False

        return True

    def _preencher_campos(self, filme):
        self.campo_titulo.setText(filme.titulo)
        indice_genero = self.combo_genero.findText(filme.genero)
        if indice_genero >= 0:
            self.combo_genero.setCurrentIndex(indice_genero)
        self.campo_ano.setValue(filme.ano)
        self.campo_duracao.setValue(filme.duracao)

        indice_status = self.combo_status.findData(filme.disponivel)
        if indice_status >= 0:
            self.combo_status.setCurrentIndex(indice_status)
