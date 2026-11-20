import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid


@unittest.skipUnless(
    os.getenv('RUN_POSTGRES_INTEGRATION') == '1',
    'Requer o perfil Docker test e RUN_POSTGRES_INTEGRATION=1.',
)
class FilmesPostgresIntegrationTest(unittest.TestCase):
    base_url = os.getenv('FILMES_TEST_API_BASE_URL', 'http://127.0.0.1:8001')

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{self.base_url}{path}',
            data=data,
            method=method,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            body = error.read()
            return error.code, json.loads(body) if body else None

    def test_crud_e_persistencia_no_postgresql_de_teste(self):
        titulo = f'Filme integracao {uuid.uuid4()}'
        dados = {
            'titulo': titulo,
            'genero': 'Teste',
            'ano': 2026,
            'duracao': 90,
            'disponivel': True,
        }
        filme_id = None
        try:
            status, criado = self.request('POST', '/filmes', dados)
            self.assertEqual(status, 201)
            filme_id = criado['id']

            status, consultado = self.request('GET', f'/filmes/{filme_id}')
            self.assertEqual(status, 200)
            self.assertEqual(consultado['titulo'], titulo)

            query = urllib.parse.urlencode({'titulo': titulo})
            status, encontrados = self.request('GET', f'/filmes?{query}')
            self.assertEqual(status, 200)
            self.assertEqual([item['id'] for item in encontrados], [filme_id])

            dados['titulo'] = f'{titulo} atualizado'
            status, atualizado = self.request('PUT', f'/filmes/{filme_id}', dados)
            self.assertEqual(status, 200)
            self.assertEqual(atualizado['titulo'], dados['titulo'])

            dados['disponivel'] = False
            status, _ = self.request('PUT', f'/filmes/{filme_id}', dados)
            self.assertEqual(status, 200)
            status, conflito = self.request('DELETE', f'/filmes/{filme_id}')
            self.assertEqual(status, 409)
            self.assertIn('alugado', conflito['detail'])

            dados['disponivel'] = True
            self.assertEqual(
                self.request('PUT', f'/filmes/{filme_id}', dados)[0],
                200,
            )
            self.assertEqual(
                self.request('DELETE', f'/filmes/{filme_id}')[0],
                204,
            )
            filme_id = None
        finally:
            if filme_id is not None:
                dados['disponivel'] = True
                self.request('PUT', f'/filmes/{filme_id}', dados)
                self.request('DELETE', f'/filmes/{filme_id}')


if __name__ == '__main__':
    unittest.main()
