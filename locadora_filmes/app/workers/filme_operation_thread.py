from collections.abc import Callable

from PySide6.QtCore import QThread, Signal


class FilmeOperationThread(QThread):
    """Executa uma operacao HTTP de filme fora da thread grafica."""

    sucesso = Signal(object)
    erro = Signal(str)

    def __init__(self, operacao: Callable, *args, parent=None, **kwargs):
        """Armazena a chamada que sera executada em segundo plano."""
        super().__init__(parent)
        self.operacao = operacao
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Executa a chamada e converte excecoes em sinal de erro."""
        try:
            resultado = self.operacao(*self.args, **self.kwargs)
        except Exception as error:
            self.erro.emit(str(error) or 'Falha inesperada na operacao.')
            return
        self.sucesso.emit(resultado)
