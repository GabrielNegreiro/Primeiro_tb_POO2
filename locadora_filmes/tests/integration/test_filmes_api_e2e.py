import os
import unittest
import uuid

from app.network.api_client import (
    ApiClient,
    ApiCommunicationError,
    ApiHttpError,
    ApiTimeoutError,
)
from app.services.filme_api_service import FilmeApiService


@unittest.skipUnless(
    os.getenv('RUN_DESKTOP_API_INTEGRATION') == '1',
    'Requer api_test e RUN_DESKTOP_API_INTEGRATION=1.',
)
class FilmesDesktopApiE2ETest(unittest.TestCase):
    base_url = os.getenv(
        'LOCADORA_TEST_API_BASE_URL',
        'http://127.0.0.1:8001',
    )

    def test_crud_completo_pelo_cliente_do_desktop(self):
        client = ApiClient(self.base_url)
        service = FilmeApiService(client)
        filme_id = None
        try:
            self.assertIsInstance(service.carregar_filmes(), list)
            titulo = f'Desktop E2E {uuid.uuid4()}'
            criado = service.adicionar_filme(
                titulo,
                'Teste',
                2026,
                90,
                True,
            )
            filme_id = criado.id

            consultado = service.buscar_por_id(filme_id)
            self.assertEqual(consultado.titulo, titulo)

            atualizado = service.atualizar_filme(
                filme_id,
                f'{titulo} Atualizado',
                'Teste Integracao',
                2026,
                91,
                False,
            )
            self.assertEqual(atualizado.duracao, 91)
            self.assertTrue(atualizado.disponivel)

            service.carregar_filmes(titulo=titulo, disponivel=True)
            self.assertEqual([item.id for item in service.filmes], [filme_id])

            service.remover_filme(filme_id)
            filme_id = None
            with self.assertRaises(ApiHttpError) as contexto:
                client.get(f'/filmes/{criado.id}')
            self.assertEqual(contexto.exception.status_code, 404)
        finally:
            if filme_id is not None:
                try:
                    client.delete(f'/filmes/{filme_id}')
                except Exception:
                    pass
            client.close()

    def test_api_indisponivel_e_reportada_como_falha(self):
        client = ApiClient(
            'http://127.0.0.1:65534',
            connect_timeout=0.2,
            read_timeout=0.2,
        )
        try:
            with self.assertRaises(
                (ApiCommunicationError, ApiTimeoutError)
            ):
                FilmeApiService(client).carregar_filmes()
        finally:
            client.close()


if __name__ == '__main__':
    unittest.main()
