import json
import os
import unittest
import urllib.request


@unittest.skipUnless(
    os.getenv('RUN_POSTGRES_INTEGRATION') == '1',
    'Requer o Docker Compose ativo e RUN_POSTGRES_INTEGRATION=1.',
)
class PostgresHealthIntegrationTest(unittest.TestCase):
    def test_health_db_consulta_postgresql_real(self):
        base_url = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')

        with urllib.request.urlopen(f'{base_url}/health/db', timeout=10) as response:
            body = json.load(response)

        self.assertEqual(response.status, 200)
        self.assertEqual(body, {'status': 'ok', 'database': 'reachable'})


if __name__ == '__main__':
    unittest.main()

