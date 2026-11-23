from PySide6.QtCore import QThread, Signal


class LocacaoLoaderThread(QThread):
    """Carrega locacoes da API fora da thread grafica."""

    carregado = Signal(object)
    erro = Signal(str)

    def __init__(self, fonte, parent=None):
        """Recebe qualquer fonte que implemente carregar_locacoes()."""
        super().__init__(parent)
        self.fonte = fonte

    def run(self):
        """Executa o carregamento e publica sucesso ou erro seguro."""
        try:
            locacoes = self.fonte.carregar_locacoes()
        except Exception as excecao:
            self.erro.emit(str(excecao) or 'Falha inesperada no carregamento.')
            return

        self.carregado.emit(locacoes)