from PySide6.QtCore import QThread, Signal


class FilmeLoaderThread(QThread):
    carregado = Signal(object)
    erro = Signal(str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository

    def run(self):
        try:
            filmes = self.repository.carregar_filmes()
        except Exception as excecao:
            self.erro.emit(str(excecao))
            return

        self.carregado.emit(filmes)
