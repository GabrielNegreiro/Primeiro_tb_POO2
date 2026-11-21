import unittest
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import Base, Filme, Locacao
from backend.app.schemas.locacoes import LocacaoResponse

PASSADO = '2020-01-01'
PASSADO_PRAZO = '2020-01-10'
FUTURO = '2099-12-31'


class LocacaoApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            'sqlite://',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool,
        )
        cls.session_factory = sessionmaker(
            bind=cls.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(cls.engine)

        def override_session():
            session = cls.session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        app.dependency_overrides[get_session] = override_session
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.pop(get_session, None)
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with self.session_factory.begin() as session:
            session.execute(delete(Locacao))
            session.execute(delete(Filme))

    # --- auxiliares -------------------------------------------------------

    def criar_filme(self, **alteracoes):
        dados = {
            'titulo': 'Matrix',
            'genero': 'Ficcao',
            'ano': 1999,
            'duracao': 136,
            'disponivel': True,
        }
        dados.update(alteracoes)
        return self.client.post('/filmes', json=dados).json()['id']

    def criar_locacao(self, filme, **alteracoes):
        dados = {
            'filme_id': filme,
            'cliente_nome': 'Ana',
            'data_locacao': PASSADO,
            'data_devolucao_prevista': FUTURO,
        }
        dados.update(alteracoes)
        return self.client.post('/locacoes', json=dados)

    def disponivel(self, filme_id):
        return self.client.get(f'/filmes/{filme_id}').json()['disponivel']

    def contar_locacoes(self):
        with self.session_factory() as session:
            return session.scalar(select(func.count()).select_from(Locacao))

    # --- cadastro ---------------------------------------------------------

    def test_cadastro_valido_torna_filme_indisponivel(self):
        filme_id = self.criar_filme()

        response = self.criar_locacao(filme_id)

        self.assertEqual(response.status_code, 201)
        corpo = response.json()
        self.assertEqual(corpo['filme_id'], filme_id)
        self.assertEqual(corpo['status'], 'Em aberto')
        self.assertFalse(corpo['atrasada'])
        self.assertIsNone(corpo['data_devolucao_real'])
        self.assertFalse(self.disponivel(filme_id))

    def test_cadastro_sem_data_usa_hoje(self):
        filme_id = self.criar_filme()

        response = self.client.post(
            '/locacoes',
            json={
                'filme_id': filme_id,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['data_locacao'], date.today().isoformat())

    def test_cadastro_filme_inexistente_retorna_404(self):
        response = self.criar_locacao(999)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Filme nao encontrado.'})

    def test_cadastro_filme_indisponivel_retorna_409(self):
        filme_id = self.criar_filme(disponivel=False)

        response = self.criar_locacao(filme_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.contar_locacoes(), 0)

    def test_segunda_locacao_do_mesmo_filme_retorna_409(self):
        filme_id = self.criar_filme()
        self.assertEqual(self.criar_locacao(filme_id).status_code, 201)

        response = self.criar_locacao(filme_id, cliente_nome='Bia')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.contar_locacoes(), 1)

    def test_cadastro_invalido_retorna_422(self):
        filme_id = self.criar_filme()
        invalidos = [
            {'cliente_nome': '   '},
            {'cliente_nome': ''},
            {'filme_id': 0},
            {'data_devolucao_prevista': '2019-12-31'},
            {'data_devolucao_prevista': 'nao-e-data'},
            {'id': 5},
            {'status': 'Devolvido'},
        ]

        for alteracoes in invalidos:
            with self.subTest(alteracoes=alteracoes):
                response = self.criar_locacao(filme_id, **alteracoes)
                self.assertEqual(response.status_code, 422)

        self.assertEqual(self.contar_locacoes(), 0)
        self.assertTrue(self.disponivel(filme_id))

    # --- listagem e consulta ---------------------------------------------

    def test_listagens_todas_ativas_e_atrasadas(self):
        atrasado = self.criar_filme(titulo='Atrasado')
        no_prazo = self.criar_filme(titulo='No prazo')
        devolvido = self.criar_filme(titulo='Devolvido')
        id_atrasada = self.criar_locacao(
            atrasado, data_devolucao_prevista=PASSADO_PRAZO
        ).json()['id']
        id_prazo = self.criar_locacao(no_prazo).json()['id']
        id_devolvida = self.criar_locacao(
            devolvido, data_devolucao_prevista=PASSADO_PRAZO
        ).json()['id']
        self.client.post(f'/locacoes/{id_devolvida}/devolucao', json={})

        def ids(situacao=None):
            params = {} if situacao is None else {'situacao': situacao}
            resposta = self.client.get('/locacoes', params=params)
            self.assertEqual(resposta.status_code, 200)
            return [item['id'] for item in resposta.json()]

        self.assertEqual(ids(), [id_atrasada, id_prazo, id_devolvida])
        self.assertEqual(ids('todas'), [id_atrasada, id_prazo, id_devolvida])
        self.assertEqual(ids('ativas'), [id_atrasada, id_prazo])
        self.assertEqual(ids('atrasadas'), [id_atrasada])

    def test_situacao_invalida_retorna_422(self):
        response = self.client.get('/locacoes', params={'situacao': 'xyz'})

        self.assertEqual(response.status_code, 422)

    def test_locacao_atrasada_e_sinalizada_na_resposta(self):
        filme_id = self.criar_filme()
        locacao = self.criar_locacao(
            filme_id, data_devolucao_prevista=PASSADO_PRAZO
        ).json()

        self.assertTrue(locacao['atrasada'])

    def test_devolvida_fora_do_prazo_nao_e_atrasada(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(
            filme_id, data_devolucao_prevista=PASSADO_PRAZO
        ).json()['id']

        response = self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        self.assertEqual(response.json()['status'], 'Devolvido')
        self.assertFalse(response.json()['atrasada'])

    def test_consulta_por_id(self):
        filme_id = self.criar_filme()
        criada = self.criar_locacao(filme_id).json()

        response = self.client.get(f"/locacoes/{criada['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), criada)

    def test_consulta_inexistente_retorna_404(self):
        response = self.client.get('/locacoes/999')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Locacao nao encontrada.'})

    def test_identificador_invalido_retorna_422(self):
        self.assertEqual(self.client.get('/locacoes/0').status_code, 422)

    # --- edicao -----------------------------------------------------------

    def test_edicao_valida_preserva_data_da_locacao(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': filme_id,
                'cliente_nome': 'Bia',
                'data_devolucao_prevista': '2099-06-30',
            },
        )

        self.assertEqual(response.status_code, 200)
        corpo = response.json()
        self.assertEqual(corpo['cliente_nome'], 'Bia')
        self.assertEqual(corpo['data_devolucao_prevista'], '2099-06-30')
        self.assertEqual(corpo['data_locacao'], PASSADO)

    def test_edicao_nao_aceita_alterar_data_da_locacao(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': filme_id,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
                'data_locacao': '2021-01-01',
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_edicao_com_prazo_anterior_a_locacao_retorna_422(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': filme_id,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': '2019-01-01',
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_edicao_de_locacao_devolvida_retorna_409(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']
        self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': filme_id,
                'cliente_nome': 'Bia',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 409)

    def test_edicao_de_locacao_inexistente_retorna_404(self):
        response = self.client.put(
            '/locacoes/999',
            json={
                'filme_id': 1,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_troca_de_filme_libera_anterior_e_bloqueia_novo(self):
        antigo = self.criar_filme(titulo='Antigo')
        novo = self.criar_filme(titulo='Novo')
        locacao_id = self.criar_locacao(antigo).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': novo,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['filme_id'], novo)
        self.assertTrue(self.disponivel(antigo))
        self.assertFalse(self.disponivel(novo))

    def test_troca_para_filme_indisponivel_nao_altera_nada(self):
        antigo = self.criar_filme(titulo='Antigo')
        ocupado = self.criar_filme(titulo='Ocupado', disponivel=False)
        locacao_id = self.criar_locacao(antigo).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': ocupado,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.client.get(f'/locacoes/{locacao_id}').json()['filme_id'], antigo
        )
        self.assertFalse(self.disponivel(antigo))

    def test_troca_para_filme_inexistente_retorna_404(self):
        antigo = self.criar_filme()
        locacao_id = self.criar_locacao(antigo).json()['id']

        response = self.client.put(
            f'/locacoes/{locacao_id}',
            json={
                'filme_id': 999,
                'cliente_nome': 'Ana',
                'data_devolucao_prevista': FUTURO,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.disponivel(antigo))

    # --- devolucao --------------------------------------------------------

    def test_devolucao_valida_libera_o_filme(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.post(
            f'/locacoes/{locacao_id}/devolucao',
            json={'data_devolucao_real': '2020-01-05'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data_devolucao_real'], '2020-01-05')
        self.assertEqual(response.json()['status'], 'Devolvido')
        self.assertTrue(self.disponivel(filme_id))

    def test_devolucao_sem_corpo_usa_data_de_hoje(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.post(f'/locacoes/{locacao_id}/devolucao')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['data_devolucao_real'], date.today().isoformat()
        )

    def test_devolucao_repetida_retorna_409(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']
        self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        response = self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        self.assertEqual(response.status_code, 409)

    def test_devolucao_com_data_anterior_a_locacao_retorna_422(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.post(
            f'/locacoes/{locacao_id}/devolucao',
            json={'data_devolucao_real': '2019-12-31'},
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(self.disponivel(filme_id))

    def test_devolucao_de_locacao_inexistente_retorna_404(self):
        response = self.client.post('/locacoes/999/devolucao', json={})

        self.assertEqual(response.status_code, 404)

    def test_filme_devolvido_pode_ser_alugado_novamente(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']
        self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        response = self.criar_locacao(filme_id, cliente_nome='Bia')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.contar_locacoes(), 2)

    # --- exclusao ---------------------------------------------------------

    def test_exclusao_de_locacao_devolvida_retorna_204(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']
        self.client.post(f'/locacoes/{locacao_id}/devolucao', json={})

        response = self.client.delete(f'/locacoes/{locacao_id}')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get(f'/locacoes/{locacao_id}').status_code, 404)
        self.assertEqual(self.client.get(f'/filmes/{filme_id}').status_code, 200)

    def test_exclusao_de_locacao_aberta_retorna_409(self):
        filme_id = self.criar_filme()
        locacao_id = self.criar_locacao(filme_id).json()['id']

        response = self.client.delete(f'/locacoes/{locacao_id}')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f'/locacoes/{locacao_id}').status_code, 200)

    def test_exclusao_de_locacao_inexistente_retorna_404(self):
        self.assertEqual(self.client.delete('/locacoes/999').status_code, 404)

    # --- integridade, rollback e documentacao ----------------------------

    def test_indice_unico_parcial_impede_duas_locacoes_abertas(self):
        filme_id = self.criar_filme()
        base = dict(
            filme_id=filme_id,
            cliente_nome='Ana',
            data_locacao=date(2020, 1, 1),
            data_devolucao_prevista=date(2020, 1, 10),
        )
        with self.session_factory.begin() as session:
            session.add(Locacao(**base))

        with self.assertRaises(IntegrityError):
            with self.session_factory.begin() as session:
                session.add(Locacao(**base))

    def test_indice_unico_parcial_permite_historico_devolvido(self):
        filme_id = self.criar_filme()
        base = dict(
            filme_id=filme_id,
            cliente_nome='Ana',
            data_locacao=date(2020, 1, 1),
            data_devolucao_prevista=date(2020, 1, 10),
        )
        with self.session_factory.begin() as session:
            session.add(Locacao(**base, data_devolucao_real=date(2020, 1, 5)))
            session.add(Locacao(**base, data_devolucao_real=date(2020, 1, 6)))
            session.add(Locacao(**base))

        self.assertEqual(self.contar_locacoes(), 3)

    def test_rollback_quando_a_disponibilidade_nao_pode_ser_atualizada(self):
        filme_id = self.criar_filme()
        erro = OperationalError('UPDATE', {}, Exception('senha-secreta'))

        with patch(
            'backend.app.services.filmes.FilmeService.definir_disponibilidade',
            side_effect=erro,
        ):
            response = self.criar_locacao(filme_id)

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('senha-secreta', response.text)
        self.assertEqual(self.contar_locacoes(), 0)
        self.assertTrue(self.disponivel(filme_id))

    def test_serializacao_do_schema_de_resposta(self):
        filme_id = self.criar_filme()
        ontem = date.today() - timedelta(days=1)
        locacao = Locacao(
            id=1,
            filme_id=filme_id,
            cliente_nome='Ana',
            data_locacao=ontem - timedelta(days=5),
            data_devolucao_prevista=ontem,
        )

        resposta = LocacaoResponse.model_validate(locacao)

        self.assertEqual(resposta.status, 'Em aberto')
        self.assertTrue(resposta.atrasada)
        self.assertEqual(resposta.model_dump(mode='json')['data_devolucao_prevista'],
                         ontem.isoformat())

    def test_endpoints_aparecem_na_documentacao_openapi(self):
        caminhos = self.client.get('/openapi.json').json()['paths']

        self.assertIn('get', caminhos['/locacoes'])
        self.assertIn('post', caminhos['/locacoes'])
        self.assertIn('/locacoes/{locacao_id}', caminhos)
        self.assertIn('post', caminhos['/locacoes/{locacao_id}/devolucao'])
        self.assertIn('/filmes', caminhos)


if __name__ == '__main__':
    unittest.main()
