import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import Base, Filme
from backend.app.repositories.filmes import FilmeIntegrityConflict


class FilmeApiTest(unittest.TestCase):
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
            session.execute(delete(Filme))

    def criar_filme(self, **alteracoes):
        dados = {
            'titulo': 'Matrix',
            'genero': 'Ficcao',
            'ano': 1999,
            'duracao': 136,
            'disponivel': True,
        }
        dados.update(alteracoes)
        return self.client.post('/filmes', json=dados)

    def test_cadastro_valido_e_consulta_por_id(self):
        criado = self.criar_filme()

        self.assertEqual(criado.status_code, 201)
        filme_id = criado.json()['id']
        consultado = self.client.get(f'/filmes/{filme_id}')
        self.assertEqual(consultado.status_code, 200)
        self.assertEqual(consultado.json(), criado.json())

    def test_cadastro_invalido_retorna_422(self):
        invalidos = [
            {'titulo': '   '},
            {'genero': ''},
            {'ano': 1500},
            {'duracao': 0},
            {'id': 99},
        ]

        for alteracoes in invalidos:
            with self.subTest(alteracoes=alteracoes):
                response = self.criar_filme(**alteracoes)
                self.assertEqual(response.status_code, 422)

    def test_listagem(self):
        self.criar_filme(titulo='Matrix')
        self.criar_filme(titulo='Toy Story', genero='Animacao', ano=1995)

        response = self.client.get('/filmes')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['titulo'] for item in response.json()], [
            'Matrix',
            'Toy Story',
        ])

    def test_consulta_inexistente_retorna_404(self):
        response = self.client.get('/filmes/999')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Filme nao encontrado.'})

    def test_pesquisa_por_titulo_sem_diferenciar_maiusculas(self):
        self.criar_filme(titulo='Matrix')
        self.criar_filme(titulo='Toy Story', genero='Animacao', ano=1995)

        response = self.client.get('/filmes', params={'titulo': 'matrix'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['titulo'], 'Matrix')

    def test_filtra_filmes_disponiveis(self):
        self.criar_filme(titulo='Disponivel')
        self.criar_filme(titulo='Alugado', disponivel=False)

        response = self.client.get('/filmes', params={'disponivel': 'true'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['titulo'] for item in response.json()], ['Disponivel'])

    def test_atualizacao(self):
        filme_id = self.criar_filme().json()['id']
        dados = {
            'titulo': 'Matrix Reloaded',
            'genero': 'Ficcao',
            'ano': 2003,
            'duracao': 138,
            'disponivel': True,
        }

        response = self.client.put(f'/filmes/{filme_id}', json=dados)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['titulo'], 'Matrix Reloaded')
        self.assertEqual(self.client.get(f'/filmes/{filme_id}').json()['ano'], 2003)

    def test_exclusao(self):
        filme_id = self.criar_filme().json()['id']

        response = self.client.delete(f'/filmes/{filme_id}')

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(self.client.get(f'/filmes/{filme_id}').status_code, 404)

    def test_exclusao_inexistente_retorna_404(self):
        response = self.client.delete('/filmes/999')

        self.assertEqual(response.status_code, 404)

    def test_exclusao_de_filme_indisponivel_retorna_409(self):
        filme_id = self.criar_filme(disponivel=False).json()['id']

        response = self.client.delete(f'/filmes/{filme_id}')

        self.assertEqual(response.status_code, 409)
        self.assertIn('alugado', response.json()['detail'])

    def test_exclusao_com_referencia_de_locacao_retorna_409(self):
        filme_id = self.criar_filme().json()['id']
        with patch(
            'backend.app.repositories.filmes.FilmeRepository.excluir',
            side_effect=FilmeIntegrityConflict,
        ):
            response = self.client.delete(f'/filmes/{filme_id}')

        self.assertEqual(response.status_code, 409)
        self.assertIn('locacoes', response.json()['detail'])

    def test_falha_de_banco_retorna_503_sem_detalhes(self):
        error = OperationalError('SELECT', {}, Exception('senha-secreta'))
        with patch(
            'backend.app.repositories.filmes.FilmeRepository.listar',
            side_effect=error,
        ):
            response = self.client.get('/filmes')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {'detail': 'Falha ao acessar o banco de dados.'},
        )
        self.assertNotIn('senha-secreta', response.text)


if __name__ == '__main__':
    unittest.main()

