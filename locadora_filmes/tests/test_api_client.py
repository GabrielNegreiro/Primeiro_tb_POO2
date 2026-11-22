import os
import unittest
from unittest.mock import patch

import httpx

from app.network.api_client import (
    ApiClient,
    ApiCommunicationError,
    ApiHttpError,
    ApiInvalidResponseError,
    ApiSerializationError,
    ApiTimeoutError,
)


class ApiClientTest(unittest.TestCase):
    def setUp(self):
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()

    def criar_client(self, handler, **kwargs):
        client = ApiClient(
            'http://api.test',
            transport=httpx.MockTransport(handler),
            **kwargs,
        )
        self.clients.append(client)
        return client

    def test_url_pode_ser_configurada_por_variavel_de_ambiente(self):
        with patch.dict(
            os.environ,
            {'LOCADORA_API_BASE_URL': 'https://locadora.exemplo/api/'},
        ):
            client = ApiClient(
                transport=httpx.MockTransport(
                    lambda _request: httpx.Response(200, json=[])
                )
            )
            self.clients.append(client)

        self.assertEqual(client.base_url, 'https://locadora.exemplo/api')

    def test_get_post_put_e_delete(self):
        recebidas = []

        def handler(request):
            recebidas.append(request)
            if request.method == 'DELETE':
                return httpx.Response(204)
            return httpx.Response(200, json={'metodo': request.method})

        client = self.criar_client(handler)

        self.assertEqual(
            client.get('/filmes', params={'disponivel': 'true'}),
            {'metodo': 'GET'},
        )
        self.assertEqual(
            client.post('/filmes', json={'titulo': 'Matrix'}),
            {'metodo': 'POST'},
        )
        self.assertEqual(
            client.put('/filmes/1', json={'titulo': 'Matrix 2'}),
            {'metodo': 'PUT'},
        )
        self.assertIsNone(client.delete('/filmes/1'))
        self.assertEqual(
            [request.method for request in recebidas],
            ['GET', 'POST', 'PUT', 'DELETE'],
        )
        self.assertIn('disponivel=true', str(recebidas[0].url))

    def test_status_http_sao_traduzidos_sem_detalhes_internos(self):
        for status in (404, 409, 422, 500, 503):
            with self.subTest(status=status):
                client = self.criar_client(
                    lambda _request, status=status: httpx.Response(
                        status,
                        json={'detail': 'senha-do-banco'},
                    )
                )
                with self.assertRaises(ApiHttpError) as contexto:
                    client.get('/filmes/99')
                self.assertEqual(contexto.exception.status_code, status)
                self.assertNotIn('senha-do-banco', str(contexto.exception))

    def test_timeout_tem_mensagem_de_dominio(self):
        def handler(request):
            raise httpx.ReadTimeout('demorou', request=request)

        client = self.criar_client(handler)

        with self.assertRaisesRegex(ApiTimeoutError, 'tempo esperado'):
            client.get('/filmes')

    def test_falha_de_conexao_nao_vira_lista_vazia(self):
        def handler(request):
            raise httpx.ConnectError('offline', request=request)

        client = self.criar_client(handler)

        with self.assertRaisesRegex(ApiCommunicationError, 'conectar'):
            client.get('/filmes')

    def test_json_invalido_e_detectado(self):
        client = self.criar_client(
            lambda _request: httpx.Response(
                200,
                content=b'{invalido',
                headers={'content-type': 'application/json'},
            )
        )

        with self.assertRaisesRegex(ApiInvalidResponseError, 'JSON invalida'):
            client.get('/filmes')

    def test_falha_de_serializacao_e_traduzida(self):
        client = self.criar_client(
            lambda _request: httpx.Response(201, json={})
        )

        with self.assertRaises(ApiSerializationError):
            client.post('/filmes', json={'invalido': object()})


if __name__ == '__main__':
    unittest.main()
