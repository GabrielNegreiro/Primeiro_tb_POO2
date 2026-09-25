import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.models.filme import Filme
from app.services.filme_service import FilmeService
from app.services.locacao_service import LocacaoService
from app.views.dashboard_page import DashboardPage


class DashboardPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.filmes = FilmeService([
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Toy Story', 'Animacao', 1995, 81, True),
        ])
        self.locacoes = LocacaoService()
        self.pagina = DashboardPage(self.locacoes, self.filmes)

    def test_exibe_dashboard_indicadores_e_estado_vazio(self):
        self.assertEqual(self.pagina.label_titulo.text(), 'Dashboard')
        self.assertEqual(self.pagina.label_ativas.text(), '0')
        self.assertEqual(self.pagina.label_atrasadas.text(), '0')
        self.assertEqual(self.pagina.label_disponiveis.text(), '2')
        self.assertFalse(self.pagina.tabela_recentes.isVisible())

    def test_atualiza_tabela_com_locacao(self):
        self.locacoes.criar_locacao(self.filmes.obter_filme(1), 'Ana', 7)
        self.pagina.atualizar_resumo()

        self.assertEqual(self.pagina.label_ativas.text(), '1')
        self.assertEqual(self.pagina.label_disponiveis.text(), '1')
        self.assertEqual(self.pagina.tabela_recentes.rowCount(), 1)
        self.assertEqual(self.pagina.tabela_recentes.item(0, 0).text(), 'Matrix')


if __name__ == '__main__':
    unittest.main()
