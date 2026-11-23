import os
import threading
import unittest
from datetime import date
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication, QDialog

from app.models.filme import Filme
from app.models.locacao_api import LocacaoApi
from app.views.dashboard_page import DashboardPage
from app.views.locacao_dialog import LocacaoDialog
from app.views.locacoes_page import LocacoesPage


def filme(id):
    return Filme(id, f'Filme {id}', 'Drama', 2000, 100, True)


def locacao(id, filme_id=1, devolvida=False):
    return LocacaoApi(
        id=id,
        filme_id=filme_id,
        cliente_nome=f'Cliente {id}',
        data_locacao=date(2026, 11, 22),
        data_devolucao_prevista=date(2026, 11, 29),
        data_devolucao_real=date(2026, 11, 23) if devolvida else None,
        status='Devolvido' if devolvida else 'Em aberto',
        atrasada=False,
        filme=filme(filme_id),
    )


class FilmesFalsos:
    def __init__(self, filmes):
        self.filmes = list(filmes)

    def listar_disponiveis(self):
        return [f for f in self.filmes if f.disponivel]


class ServicoFalso:
    assincrono = True

    def __init__(self, locacoes=(), carregado=True):
        self.locacoes = list(locacoes)
        self.carregado = carregado
        self.chamadas = []
        self.erro = None
        self.trava = None

    def listar_todas(self):
        return list(self.locacoes)

    def listar_ativas(self):
        return [l for l in self.locacoes if l.status == 'Em aberto']

    def listar_atrasadas(self):
        return [l for l in self.locacoes if l.atrasada]

    def obter_locacao(self, locacao_id):
        return next((l for l in self.locacoes if l.id == locacao_id), None)

    def _executar(self, nome, identificador):
        if self.trava is not None:
            self.trava.wait(5)
        if self.erro is not None:
            raise self.erro
        self.chamadas.append((nome, identificador))

    def criar_locacao(self, filme, cliente_nome, dias_previstos=7):
        self._executar('criar', filme.id)
        nova = locacao(len(self.locacoes) + 1, filme_id=filme.id)
        self.locacoes.append(nova)
        return nova

    def devolver_locacao(self, locacao_id):
        self._executar('devolver', locacao_id)
        atual = self.obter_locacao(locacao_id)
        atual.status = 'Devolvido'
        atual.data_devolucao_real = date(2026, 11, 23)
        return atual

    def atualizar_filmes(self):
        self.chamadas.append(('filmes', None))


def dialogo_falso(dados):
    class Dialogo:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def dados(self):
            return dados

    return Dialogo


class LocacoesPageHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def criar_pagina(self, servico):
        pagina = LocacoesPage(servico, FilmesFalsos([filme(1), filme(2)]))
        self.addCleanup(pagina.deleteLater)
        return pagina

    def esperar(self, pagina):
        thread = pagina.operacao_thread
        if thread is not None:
            self.assertTrue(thread.wait(5000))
        for _ in range(3):
            self.app.processEvents()

    def test_cadastro_chama_api_atualiza_filmes_e_confirma(self):
        servico = ServicoFalso()
        pagina = self.criar_pagina(servico)
        emitidos = []
        pagina.locacoes_alteradas.connect(lambda: emitidos.append(1))

        with patch(
            'app.views.locacoes_page.LocacaoDialog',
            dialogo_falso(
                {'filme': filme(2), 'cliente_nome': 'Ana', 'dias': 7}
            ),
        ), patch(
            'app.views.locacoes_page.QMessageBox.information'
        ) as informacao:
            pagina.abrir_nova_locacao()
            self.assertFalse(pagina.botao_nova.isEnabled())
            self.esperar(pagina)

        self.assertEqual(servico.chamadas, [('criar', 2), ('filmes', None)])
        self.assertEqual(pagina.tabela.rowCount(), 1)
        self.assertEqual(emitidos, [1])
        informacao.assert_called_once()
        self.assertTrue(pagina.botao_nova.isEnabled())
        self.assertIsNone(pagina.operacao_thread)

    def test_falha_http_nao_mostra_sucesso_nem_altera_a_tabela(self):
        servico = ServicoFalso([locacao(1)])
        servico.erro = RuntimeError('Filme indisponivel para locacao.')
        pagina = self.criar_pagina(servico)

        with patch(
            'app.views.locacoes_page.LocacaoDialog',
            dialogo_falso(
                {'filme': filme(2), 'cliente_nome': 'Ana', 'dias': 7}
            ),
        ), patch(
            'app.views.locacoes_page.QMessageBox.information'
        ) as informacao, patch(
            'app.views.locacoes_page.QMessageBox.warning'
        ) as aviso:
            pagina.abrir_nova_locacao()
            self.esperar(pagina)

        informacao.assert_not_called()
        aviso.assert_called_once()
        self.assertIn('indisponivel', aviso.call_args.args[2])
        self.assertEqual(pagina.tabela.rowCount(), 1)
        self.assertTrue(pagina.botao_nova.isEnabled())

    def test_devolucao_usa_o_id_da_locacao_selecionada(self):
        servico = ServicoFalso([locacao(1), locacao(2)])
        pagina = self.criar_pagina(servico)
        pagina.tabela.selectRow(1)

        with patch('app.views.locacoes_page.QMessageBox.information'):
            pagina.devolver_selecionada()
            self.esperar(pagina)

        self.assertIn(('devolver', 2), servico.chamadas)
        self.assertEqual(servico.obter_locacao(2).status, 'Devolvido')

    def test_selecao_acompanha_o_id_apos_atualizar_a_tabela(self):
        servico = ServicoFalso([locacao(1), locacao(2)])
        pagina = self.criar_pagina(servico)
        pagina.tabela.selectRow(1)

        servico.locacoes.reverse()
        pagina.atualizar_tabela()

        self.assertEqual(pagina.locacao_selecionada().id, 2)

    def test_operacao_duplicada_e_bloqueada(self):
        servico = ServicoFalso([locacao(1)])
        servico.trava = threading.Event()
        pagina = self.criar_pagina(servico)
        pagina.tabela.selectRow(0)

        with patch('app.views.locacoes_page.QMessageBox.information'):
            pagina.devolver_selecionada()
            self.assertTrue(pagina.operacao_em_andamento())
            self.assertFalse(pagina.botao_devolver.isEnabled())
            pagina.devolver_selecionada()
            servico.trava.set()
            self.esperar(pagina)

        self.assertEqual(
            [c for c in servico.chamadas if c[0] == 'devolver'],
            [('devolver', 1)],
        )

    def test_exclusao_de_locacao_aberta_e_recusada_sem_chamar_a_api(self):
        servico = ServicoFalso([locacao(1)])
        pagina = self.criar_pagina(servico)
        pagina.tabela.selectRow(0)

        with patch('app.views.locacoes_page.QMessageBox.warning') as aviso:
            pagina.excluir_selecionada()

        aviso.assert_called_once()
        self.assertIsNone(pagina.operacao_thread)
        self.assertEqual(servico.chamadas, [])

    def test_exportar_sem_dados_carregados_nao_abre_dialogo(self):
        pagina = self.criar_pagina(ServicoFalso(carregado=False))

        with patch(
            'app.views.locacoes_page.QFileDialog.getSaveFileName'
        ) as salvar, patch(
            'app.views.locacoes_page.QMessageBox.information'
        ) as informacao:
            pagina.exportar_relatorio()

        salvar.assert_not_called()
        informacao.assert_called_once()
        self.assertIsNone(pagina.thread_exportacao)


class LocacaoDialogHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dialogo_apenas_coleta_os_dados(self):
        filmes = [filme(1), filme(2)]
        dialog = LocacaoDialog(filmes, ServicoFalso())
        dialog.campo_cliente.setText(' Ana ')
        dialog.combo_filme.setCurrentIndex(1)
        dialog.campo_dias.setValue(5)

        dialog.salvar()

        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(
            dialog.dados(),
            {'filme': filmes[1], 'cliente_nome': 'Ana', 'dias': 5},
        )

    def test_edicao_seleciona_o_filme_pelo_id(self):
        filmes = [filme(1), filme(2)]
        existente = locacao(3, filme_id=2)
        existente.filme = None

        dialog = LocacaoDialog(
            filmes, ServicoFalso(), locacao=existente
        )

        self.assertEqual(dialog.combo_filme.currentData().id, 2)
        self.assertEqual(dialog.campo_cliente.text(), 'Cliente 3')


class DashboardHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_nao_mostra_zero_enquanto_nao_carregou(self):
        servico = ServicoFalso(carregado=False)
        pagina = DashboardPage(servico, FilmesFalsos([filme(1)]))

        self.assertEqual(pagina.label_ativas.text(), '-')
        self.assertEqual(pagina.label_disponiveis.text(), '1')

        servico.locacoes = [locacao(1)]
        servico.carregado = True
        pagina.definir_locacoes_integradas()

        self.assertEqual(pagina.label_ativas.text(), '1')
        self.assertEqual(pagina.tabela_recentes.item(0, 0).text(), 'Filme 1')

    def test_falha_de_carregamento_volta_a_indisponivel(self):
        pagina = DashboardPage(ServicoFalso(), FilmesFalsos([]))

        pagina.definir_locacoes_indisponiveis('API fora do ar.')

        self.assertEqual(pagina.label_ativas.text(), '-')
        self.assertEqual(pagina.label_atrasadas.text(), '-')


if __name__ == '__main__':
    unittest.main()