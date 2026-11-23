from collections.abc import Callable
from typing import Optional

from PySide6.QtCore import QThread, Signal


class LocacaoOperationThread(QThread):
    """Executa uma operacao HTTP de locacao fora da thread grafica."""

    sucesso = Signal(object)
    erro = Signal(str)
    # A operacao foi concluida no servidor, mas o acervo nao foi atualizado.
    sucesso_sem_atualizacao = Signal(object, str)

    def __init__(
        self,
        operacao: Callable,
        *args,
        atualizar_filmes: Optional[Callable] = None,
        parent=None,
        **kwargs,
    ):
        """Armazena a chamada e a atualizacao opcional do acervo."""
        super().__init__(parent)
        self.operacao = operacao
        self.args = args
        self.kwargs = kwargs
        self.atualizar_filmes = atualizar_filmes

    def run(self):
        """Executa a operacao uma unica vez e depois atualiza o acervo."""
        try:
            resultado = self.operacao(*self.args, **self.kwargs)
        except Exception as error:
            self.erro.emit(str(error) or 'Falha inesperada na operacao.')
            return

        if self.atualizar_filmes is not None:
            try:
                self.atualizar_filmes()
            except Exception as error:
                self.sucesso_sem_atualizacao.emit(
                    resultado,
                    str(error) or 'Falha ao atualizar o acervo.',
                )
                return
        self.sucesso.emit(resultado)