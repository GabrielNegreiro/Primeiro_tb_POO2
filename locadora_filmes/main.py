import sys

from PySide6.QtWidgets import QApplication

from app.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    janela = MainWindow()
    janela.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
