import unittest
from datetime import date
from types import SimpleNamespace

from pydantic import ValidationError

from backend.app.schemas.locacoes import (
    FiltroLocacao,
    LocacaoCreate,
    LocacaoDevolucaoRequest,
    LocacaoResponse,
    LocacaoUpdate,
)

LOCACAO = date(2026, 11, 13)
PREVISTA = date(2026, 11, 20)


class LocacaoCreateTest(unittest.TestCase):
    def _dados(self, **extra):
        base = dict(
            filme_id=1,
            cliente_nome='Ana',
            data_locacao=LOCACAO,
            data_devolucao_prevista=PREVISTA,
        )
        base.update(extra)
        return base

    def test_aceita_dados_validos(self):
        dados = LocacaoCreate(**self._dados())
        self.assertEqual(dados.filme_id, 1)
        self.assertEqual(dados.cliente_nome, 'Ana')
        self.assertEqual(dados.data_locacao, LOCACAO)
        self.assertEqual(dados.data_devolucao_prevista, PREVISTA)

    def test_data_da_locacao_padrao_e_hoje(self):
        dados = LocacaoCreate(
            filme_id=1, cliente_nome='Ana', data_devolucao_prevista=date(2999, 1, 1)
        )
        self.assertEqual(dados.data_locacao, date.today())

    def test_remove_espacos_do_nome(self):
        dados = LocacaoCreate(**self._dados(cliente_nome='  Ana  '))
        self.assertEqual(dados.cliente_nome, 'Ana')

    def test_rejeita_filme_id_invalido(self):
        for filme_id in (0, -1):
            with self.subTest(filme_id=filme_id):
                with self.assertRaises(ValidationError):
                    LocacaoCreate(**self._dados(filme_id=filme_id))

    def test_rejeita_nome_vazio_ou_so_espacos(self):
        for nome in ('', '   '):
            with self.subTest(nome=nome):
                with self.assertRaises(ValidationError):
                    LocacaoCreate(**self._dados(cliente_nome=nome))

    def test_aceita_prevista_no_mesmo_dia_da_locacao(self):
        dados = LocacaoCreate(**self._dados(data_devolucao_prevista=LOCACAO))
        self.assertEqual(dados.data_devolucao_prevista, LOCACAO)

    def test_rejeita_prevista_anterior_a_locacao(self):
        with self.assertRaises(ValidationError):
            LocacaoCreate(**self._dados(data_devolucao_prevista=date(2026, 11, 12)))

    def test_rejeita_campos_gerados_pelo_banco_ou_calculados(self):
        for campo, valor in (('id', 5), ('status', 'Devolvido'), ('atrasada', True)):
            with self.subTest(campo=campo):
                with self.assertRaises(ValidationError):
                    LocacaoCreate(**self._dados(**{campo: valor}))

    def test_exige_data_prevista(self):
        with self.assertRaises(ValidationError):
            LocacaoCreate(filme_id=1, cliente_nome='Ana', data_locacao=LOCACAO)

    def test_aceita_datas_em_formato_iso(self):
        dados = LocacaoCreate(
            **self._dados(data_locacao='2026-11-13', data_devolucao_prevista='2026-11-20')
        )
        self.assertEqual(dados.data_locacao, LOCACAO)
        self.assertEqual(dados.data_devolucao_prevista, PREVISTA)


class LocacaoUpdateTest(unittest.TestCase):
    def test_aceita_dados_validos(self):
        dados = LocacaoUpdate(
            filme_id=2, cliente_nome=' Bia ', data_devolucao_prevista=PREVISTA
        )
        self.assertEqual(dados.filme_id, 2)
        self.assertEqual(dados.cliente_nome, 'Bia')
        self.assertEqual(dados.data_devolucao_prevista, PREVISTA)

    def test_exige_data_prevista(self):
        with self.assertRaises(ValidationError):
            LocacaoUpdate(filme_id=1, cliente_nome='Ana')

    def test_rejeita_nome_vazio(self):
        with self.assertRaises(ValidationError):
            LocacaoUpdate(filme_id=1, cliente_nome=' ', data_devolucao_prevista=PREVISTA)

    def test_rejeita_filme_id_invalido(self):
        with self.assertRaises(ValidationError):
            LocacaoUpdate(filme_id=0, cliente_nome='Ana', data_devolucao_prevista=PREVISTA)

    def test_nao_permite_alterar_a_data_da_locacao(self):
        with self.assertRaises(ValidationError):
            LocacaoUpdate(
                filme_id=1,
                cliente_nome='Ana',
                data_devolucao_prevista=PREVISTA,
                data_locacao=LOCACAO,
            )


class LocacaoDevolucaoRequestTest(unittest.TestCase):
    def test_data_e_opcional(self):
        self.assertIsNone(LocacaoDevolucaoRequest().data_devolucao_real)

    def test_aceita_data_em_formato_iso(self):
        dados = LocacaoDevolucaoRequest(data_devolucao_real='2026-11-20')
        self.assertEqual(dados.data_devolucao_real, date(2026, 11, 20))

    def test_rejeita_data_inexistente(self):
        with self.assertRaises(ValidationError):
            LocacaoDevolucaoRequest(data_devolucao_real='2026-13-45')


class LocacaoResponseTest(unittest.TestCase):
    def _objeto(self, **extra):
        base = dict(
            id=10,
            filme_id=3,
            cliente_nome='Ana',
            data_locacao=LOCACAO,
            data_devolucao_prevista=PREVISTA,
            data_devolucao_real=None,
            status='Em aberto',
            atrasada=False,
        )
        base.update(extra)
        return SimpleNamespace(**base)

    def test_monta_a_partir_de_um_objeto(self):
        resposta = LocacaoResponse.model_validate(self._objeto())
        self.assertEqual(resposta.id, 10)
        self.assertEqual(resposta.status, 'Em aberto')
        self.assertIsNone(resposta.data_devolucao_real)

    def test_serializa_datas_em_iso(self):
        dados = LocacaoResponse.model_validate(self._objeto()).model_dump(mode='json')
        self.assertEqual(dados['data_locacao'], '2026-11-13')
        self.assertEqual(dados['data_devolucao_prevista'], '2026-11-20')
        self.assertIsNone(dados['data_devolucao_real'])

    def test_rejeita_status_desconhecido(self):
        with self.assertRaises(ValidationError):
            LocacaoResponse.model_validate(self._objeto(status='Cancelada'))

    def test_aceita_locacao_devolvida(self):
        resposta = LocacaoResponse.model_validate(
            self._objeto(data_devolucao_real=date(2026, 11, 18), status='Devolvido')
        )
        self.assertEqual(resposta.data_devolucao_real, date(2026, 11, 18))

    def test_rejeita_data_real_anterior_a_locacao(self):
        with self.assertRaises(ValidationError):
            LocacaoResponse.model_validate(
                self._objeto(data_devolucao_real=date(2026, 11, 12), status='Devolvido')
            )

    def test_rejeita_prevista_anterior_a_locacao(self):
        with self.assertRaises(ValidationError):
            LocacaoResponse.model_validate(
                self._objeto(data_devolucao_prevista=date(2026, 11, 12))
            )


class FiltroLocacaoTest(unittest.TestCase):
    def test_aceita_os_tres_valores(self):
        self.assertEqual(FiltroLocacao('todas'), FiltroLocacao.TODAS)
        self.assertEqual(FiltroLocacao('ativas'), FiltroLocacao.ATIVAS)
        self.assertEqual(FiltroLocacao('atrasadas'), FiltroLocacao.ATRASADAS)

    def test_rejeita_valor_desconhecido(self):
        with self.assertRaises(ValueError):
            FiltroLocacao('canceladas')


if __name__ == '__main__':
    unittest.main()