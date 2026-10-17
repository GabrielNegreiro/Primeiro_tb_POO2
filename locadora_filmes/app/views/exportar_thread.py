from PySide6.QtCore import QThread, Signal

from app.services.relatorio_service import RelatorioService


class ExportarRelatorioThread(QThread):

    concluido = Signal(str)
    falhou = Signal(str)

    def __init__(self, locacoes, caminho, parent=None):
        super().__init__(parent)
        self.locacoes = locacoes
        self.caminho = caminho

    def run(self):
        try:
            RelatorioService().exportar_txt(self.locacoes, self.caminho)
        except OSError as erro:
            self.falhou.emit(str(erro))
            return

        self.concluido.emit(self.caminho)