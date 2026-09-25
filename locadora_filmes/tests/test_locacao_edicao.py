import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from app.models.filme import Filme
from app.services.locacao_service import LocacaoService
from app.views.locacao_dialog import LocacaoDialog
from app.views.locacoes_page import LocacoesPage


class FilmeServiceFake:
    def __init__(self, filmes):
        self.filmes = filmes

    def listar_disponiveis(self):
        return [filme for filme in self.filmes if filme.disponivel]


class LocacaoEdicaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.filme_atual = Filme(1, 'Matrix', 'Ficcao', 1999, 136, True)
        self.filme_novo = Filme(2, 'Toy Story', 'Animacao', 1995, 81, True)
        self.service = LocacaoService()
        self.locacao = self.service.criar_locacao(self.filme_atual, 'Ana', 7)

    def test_servico_atualiza_dados_e_disponibilidade(self):
        atualizada = self.service.atualizar_locacao(
            self.locacao, self.filme_novo, 'Beatriz', 10
        )

        self.assertIs(atualizada.filme, self.filme_novo)
        self.assertEqual(atualizada.cliente_nome, 'Beatriz')
        self.assertEqual(
            (atualizada.data_devolucao_prevista - atualizada.data_locacao).days,
            10,
        )
        self.assertTrue(self.filme_atual.disponivel)
        self.assertFalse(self.filme_novo.disponivel)

    def test_nao_edita_locacao_devolvida(self):
        self.service.devolver_locacao(self.locacao)

        with self.assertRaises(ValueError):
            self.service.atualizar_locacao(
                self.locacao, self.filme_novo, 'Beatriz', 10
            )

    def test_dialogo_abre_preenchido_e_salva(self):
        dialog = LocacaoDialog(
            [self.filme_atual, self.filme_novo],
            self.service,
            locacao=self.locacao,
        )

        self.assertEqual(dialog.windowTitle(), 'Editar Locacao')
        self.assertEqual(dialog.campo_cliente.text(), 'Ana')
        dialog.campo_cliente.setText('Carla')
        dialog.combo_filme.setCurrentIndex(1)
        dialog.campo_dias.setValue(12)
        dialog.salvar()

        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(self.locacao.cliente_nome, 'Carla')
        self.assertIs(self.locacao.filme, self.filme_novo)

    def test_pagina_exibe_botao_editar(self):
        filmes = FilmeServiceFake([self.filme_atual, self.filme_novo])
        pagina = LocacoesPage(self.service, filmes)
        textos = {botao.text() for botao in pagina.findChildren(QPushButton)}

        self.assertIn('Editar Selecionada', textos)


if __name__ == '__main__':
    unittest.main()
