import importlib
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.app.main import app


class BackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_backend_importa_corretamente(self):
        module = importlib.import_module('backend.app.main')

        self.assertIs(module.app, app)

    def test_aplicacao_fastapi_inicializa(self):
        self.assertIsInstance(app, FastAPI)

    def test_health_confirma_apenas_o_processo_da_api(self):
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'status': 'ok', 'service': 'locadora-api'},
        )

    def test_health_db_retorna_503_quando_banco_indisponivel(self):
        error = OperationalError('SELECT 1', {}, Exception('offline'))
        with patch(
            'backend.app.main.check_database_connection',
            side_effect=error,
        ):
            response = self.client.get('/health/db')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {'detail': 'Banco de dados indisponivel.'},
        )
        self.assertNotIn('offline', response.text)

    def test_health_db_retorna_ok_quando_consulta_funciona(self):
        with patch(
            'backend.app.main.check_database_connection',
            return_value=True,
        ):
            response = self.client.get('/health/db')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'status': 'ok', 'database': 'reachable'},
        )


if __name__ == '__main__':
    unittest.main()

