import unittest
from pathlib import Path

import yaml


class DockerComposeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compose_path = Path(__file__).resolve().parents[3] / 'docker-compose.yml'
        cls.compose = yaml.safe_load(compose_path.read_text(encoding='utf-8'))

    def test_define_api_e_postgresql(self):
        services = self.compose['services']

        self.assertIn('api', services)
        self.assertIn('db', services)
        self.assertTrue(services['api'].get('build'))
        self.assertEqual(services['db']['image'], 'postgres:16-alpine')

    def test_postgresql_tem_volume_healthcheck_e_nao_publica_porta(self):
        database = self.compose['services']['db']

        self.assertNotIn('ports', database)
        self.assertIn('healthcheck', database)
        self.assertIn(
            'postgres_data:/var/lib/postgresql/data',
            database['volumes'],
        )
        self.assertIn('postgres_data', self.compose['volumes'])

    def test_api_aguarda_banco_saudavel_e_compartilha_rede(self):
        api = self.compose['services']['api']
        database = self.compose['services']['db']

        self.assertEqual(
            api['depends_on']['db']['condition'],
            'service_healthy',
        )
        self.assertIn('backend', api['networks'])
        self.assertIn('backend', database['networks'])
        self.assertEqual(api['environment']['DATABASE_HOST'], 'db')


if __name__ == '__main__':
    unittest.main()

