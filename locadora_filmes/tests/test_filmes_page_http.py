import os
import threading
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QDialog

from app.models.filme import Filme
from app.views.filmes_page import FilmesPage


class FilmeServiceFake:
    def __init__(self):
        self.filmes = [
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
        ]

    def listar_filmes(self):
        return list(self.filmes)

    def buscar_filmes(self, texto):
        termo = texto.lower().strip()
        return [
            filme
            for filme in self.filmes
            if not termo
            or termo in filme.titulo.lower()
            or termo in filme.genero.lower()
            or termo in str(filme.ano)
        ]

    def obter_filme(self, filme_id):
        return next(
            (filme for filme in self.filmes if filme.id == filme_id),
            None,
        )

    def adicionar_filme(self, **dados):
        filme = Filme(id=2, **dados)
        self.filmes.append(filme)
        return filme

    def atualizar_filme(self, filme_id, **dados):
        filme = self.obter_filme(filme_id)
        for campo, valor in dados.items():
            setattr(filme, campo, valor)
        return filme

    def remover_filme(self, filme_id):
        filme = self.obter_filme(filme_id)
        self.filmes.remove(filme)
        return filme


class FilmesPageHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.service = FilmeServiceFake()
        self.page = FilmesPage(self.service)

    def tearDown(self):
        if self.page.operacao_em_andamento():
            self.assertTrue(self.page.aguardar_operacao(3000))
        self.app.processEvents()
        self.page.deleteLater()
        self.app.processEvents()

    def esperar_operacao(self):
        thread = self.page.operacao_thread
        self.assertIsNotNone(thread)
        self.assertTrue(thread.wait(3000))
        for _ in range(5):
            self.app.processEvents()

    def test_cadastro_assincrono_atualiza_tabela_apos_sucesso(self):
        dialog = Mock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.dados.return_value = {
            'titulo': 'Toy Story',
            'genero': 'Animacao',
            'ano': 1995,
            'duracao': 81,
            'disponivel': True,
        }

        with patch(
            'app.views.filmes_page.FilmeDialog',
            return_value=dialog,
        ) as dialog_class, patch(
            'app.views.filmes_page.QMessageBox.information'
        ) as information:
            self.page.abrir_cadastro()
            self.esperar_operacao()

        dialog_class.assert_called_once()
        self.assertFalse(
            dialog_class.call_args.kwargs['permitir_editar_disponibilidade']
        )
        self.assertEqual(self.page.tabela.rowCount(), 2)
        self.assertEqual(self.page.tabela.item(1, 1).text(), 'Toy Story')
        information.assert_called_once()

    def test_falhas_de_cadastro_edicao_e_exclusao_restauram_controles(self):
        def falhar():
            raise RuntimeError('servico temporariamente indisponivel')

        for tipo in ('cadastro', 'edicao', 'exclusao'):
            with self.subTest(tipo=tipo), patch(
                'app.views.filmes_page.QMessageBox.warning'
            ) as warning:
                self.assertTrue(
                    self.page._executar_operacao(tipo, falhar)
                )
                self.esperar_operacao()
                warning.assert_called_once()
                self.assertIn(
                    'temporariamente indisponivel',
                    warning.call_args.args[2],
                )
                self.assertTrue(self.page.botao_novo.isEnabled())

    def test_requisicao_duplicada_e_impedida(self):
        iniciou = threading.Event()
        liberar = threading.Event()

        def operacao_lenta():
            iniciou.set()
            liberar.wait(2)
            return self.service.filmes[0]

        with patch('app.views.filmes_page.QMessageBox.information'):
            self.assertTrue(
                self.page._executar_operacao('edicao', operacao_lenta)
            )
            self.assertTrue(iniciou.wait(1))
            segunda = self.page._executar_operacao(
                'exclusao',
                self.service.remover_filme,
                1,
            )
            self.assertFalse(segunda)
            liberar.set()
            self.esperar_operacao()

        self.assertIsNotNone(self.service.obter_filme(1))

    def test_carregamento_desabilita_operacoes_sem_apagar_tabela(self):
        self.page.set_carregando(True)

        self.assertFalse(self.page.botao_novo.isEnabled())
        self.assertEqual(self.page.tabela.rowCount(), 1)

        self.page.set_carregando(False)
        self.assertTrue(self.page.botao_novo.isEnabled())


if __name__ == '__main__':
    unittest.main()
