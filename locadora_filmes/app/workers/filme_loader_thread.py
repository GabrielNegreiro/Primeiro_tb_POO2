from PySide6.QtCore import QThread, Signal


class FilmeLoaderThread(QThread):
    """Carrega filmes de uma fonte local ou HTTP fora da thread grafica."""

    carregado = Signal(object)
    erro = Signal(str)

    def __init__(self, fonte, parent=None):
        """Recebe qualquer fonte que implemente carregar_filmes()."""
        super().__init__(parent)
        self.fonte = fonte
        # Mantido para compatibilidade com os testes e contratos antigos.
        self.repository = fonte

    def run(self):
        """Executa o carregamento e publica sucesso ou erro seguro."""
        try:
            filmes = self.fonte.carregar_filmes()
        except Exception as excecao:
            self.erro.emit(str(excecao) or 'Falha inesperada no carregamento.')
            return

        self.carregado.emit(filmes)
