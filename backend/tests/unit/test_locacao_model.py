import ast
import unittest
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint

from backend.app.models import Base, Filme, Locacao

MIGRACAO = (
    Path(__file__).resolve().parents[2]
    / 'alembic'
    / 'versions'
    / '20261120_02_create_locacoes.py'
)


class LocacaoModelTest(unittest.TestCase):
    def test_tabelas_registradas_na_metadata_compartilhada(self):
        self.assertIn('filmes', Base.metadata.tables)
        self.assertIn('locacoes', Base.metadata.tables)
        self.assertIs(Locacao.metadata, Filme.metadata)

    def test_colunas_e_obrigatoriedade(self):
        colunas = Locacao.__table__.c
        self.assertEqual(
            list(colunas.keys()),
            [
                'id',
                'filme_id',
                'cliente_nome',
                'data_locacao',
                'data_devolucao_prevista',
                'data_devolucao_real',
            ],
        )
        self.assertFalse(colunas.filme_id.nullable)
        self.assertFalse(colunas.cliente_nome.nullable)
        self.assertFalse(colunas.data_locacao.nullable)
        self.assertFalse(colunas.data_devolucao_prevista.nullable)
        self.assertTrue(colunas.data_devolucao_real.nullable)
        self.assertNotIn('status', colunas)
        self.assertNotIn('atrasada', colunas)

    def test_chave_estrangeira_restrict_para_filmes(self):
        chaves = [
            c
            for c in Locacao.__table__.constraints
            if isinstance(c, ForeignKeyConstraint)
        ]
        self.assertEqual(len(chaves), 1)
        self.assertEqual(chaves[0].ondelete, 'RESTRICT')
        self.assertEqual(list(chaves[0].elements)[0].target_fullname, 'filmes.id')

    def test_restricoes_de_datas(self):
        nomes = {
            c.name
            for c in Locacao.__table__.constraints
            if isinstance(c, CheckConstraint)
        }
        self.assertEqual(
            nomes,
            {
                'ck_locacoes_prevista_apos_locacao',
                'ck_locacoes_real_apos_locacao',
            },
        )

    def test_indice_unico_parcial_de_locacao_aberta(self):
        indices = {i.name: i for i in Locacao.__table__.indexes}
        indice = indices['uq_locacoes_filme_em_aberto']

        self.assertTrue(indice.unique)
        self.assertEqual([c.name for c in indice.columns], ['filme_id'])
        self.assertEqual(
            str(indice.dialect_options['postgresql']['where']),
            'data_devolucao_real IS NULL',
        )

    def test_status_e_atrasada_sao_derivados(self):
        hoje = date.today()
        aberta_no_prazo = Locacao(
            data_locacao=hoje,
            data_devolucao_prevista=hoje + timedelta(days=3),
        )
        aberta_atrasada = Locacao(
            data_locacao=hoje - timedelta(days=10),
            data_devolucao_prevista=hoje - timedelta(days=1),
        )
        devolvida_atrasada = Locacao(
            data_locacao=hoje - timedelta(days=10),
            data_devolucao_prevista=hoje - timedelta(days=5),
            data_devolucao_real=hoje,
        )

        self.assertEqual((aberta_no_prazo.status, aberta_no_prazo.atrasada),
                         ('Em aberto', False))
        self.assertEqual((aberta_atrasada.status, aberta_atrasada.atrasada),
                         ('Em aberto', True))
        self.assertEqual((devolvida_atrasada.status, devolvida_atrasada.atrasada),
                         ('Devolvido', False))

    def test_migracao_depende_da_revisao_de_filmes(self):
        arvore = ast.parse(MIGRACAO.read_text(encoding='utf-8'))
        valores = {}
        for no in arvore.body:
            if isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
                if no.target.id in ('revision', 'down_revision'):
                    valores[no.target.id] = ast.literal_eval(no.value)

        self.assertEqual(valores['revision'], '20261120_02')
        self.assertEqual(valores['down_revision'], '20261120_01')

if __name__ == '__main__':
    unittest.main()
