import os
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QDialog

from app.models.filme import Filme
from app.views.filme_dialog import FilmeDialog


class FilmeDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_criacao_do_dialog_e_campos(self):
        dialog = FilmeDialog()
        self.assertIsNotNone(dialog.campo_titulo)
        self.assertIsNotNone(dialog.combo_genero)
        self.assertIsNotNone(dialog.campo_ano)
        self.assertIsNotNone(dialog.campo_duracao)
        self.assertIsNotNone(dialog.combo_status)

    def test_preenchimento_e_dados(self):
        dialog = FilmeDialog()
        dialog.campo_titulo.setText('Teste')
        dialog.combo_genero.setCurrentText('Drama')
        dialog.campo_ano.setValue(2022)
        dialog.campo_duracao.setValue(120)

        dados = dialog.dados()

        self.assertEqual(dados['titulo'], 'Teste')
        self.assertEqual(dados['genero'], 'Drama')
        self.assertEqual(dados['ano'], 2022)
        self.assertEqual(dados['duracao'], 120)

    def test_validacao_basica(self):
        dialog = FilmeDialog()
        dialog.campo_titulo.clear()
        with patch('app.views.filme_dialog.QMessageBox.warning') as warning:
            self.assertFalse(dialog.validar())
            warning.assert_called_once()

    def test_modo_cadastro_e_edicao(self):
        cadastro = FilmeDialog()
        edicao = FilmeDialog(Filme(1, 'Matrix', 'Ficcao', 1999, 136, True))

        self.assertEqual(cadastro.windowTitle(), 'Novo Filme')
        self.assertEqual(edicao.windowTitle(), 'Editar Filme')
        self.assertEqual(edicao.campo_titulo.text(), 'Matrix')

    def test_salvar_aceita_dialog_valido(self):
        dialog = FilmeDialog()
        dialog.campo_titulo.setText('Filme Valido')
        dialog.campo_duracao.setValue(90)
        dialog.salvar()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)


if __name__ == '__main__':
    unittest.main()
