import json
import os
import threading
import unittest
import urllib.error
import urllib.request
import uuid


@unittest.skipUnless(
    os.getenv('RUN_POSTGRES_INTEGRATION') == '1',
    'Requer o perfil Docker test e RUN_POSTGRES_INTEGRATION=1.',
)
class LocacoesPostgresIntegrationTest(unittest.TestCase):
    base_url = os.getenv('FILMES_TEST_API_BASE_URL', 'http://127.0.0.1:8001')
    FUTURO = '2099-12-31'

    def setUp(self):
        self.filmes = []
        self.locacoes = []
        self.addCleanup(self._limpar)

    def _limpar(self):
        for locacao_id in self.locacoes:
            self.request('POST', f'/locacoes/{locacao_id}/devolucao', {})
            self.request('DELETE', f'/locacoes/{locacao_id}')
        for filme_id in self.filmes:
            self.request('DELETE', f'/filmes/{filme_id}')

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            f'{self.base_url}{path}',
            data=data,
            method=method,
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read()
                return response.status, json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            body = error.read()
            return error.code, json.loads(body) if body else None

    def novo_filme(self):
        status, filme = self.request(
            'POST',
            '/filmes',
            {
                'titulo': f'Filme locacao {uuid.uuid4()}',
                'genero': 'Teste',
                'ano': 2026,
                'duracao': 90,
                'disponivel': True,
            },
        )
        self.assertEqual(status, 201)
        self.filmes.append(filme['id'])
        return filme['id']

    def nova_locacao(self, filme_id, cliente='Cliente integracao'):
        return self.request(
            'POST',
            '/locacoes',
            {
                'filme_id': filme_id,
                'cliente_nome': cliente,
                'data_devolucao_prevista': self.FUTURO,
            },
        )

    def disponivel(self, filme_id):
        return self.request('GET', f'/filmes/{filme_id}')[1]['disponivel']

    def test_ciclo_completo_persistido_no_postgresql(self):
        filme_id = self.novo_filme()

        status, locacao = self.nova_locacao(filme_id)
        self.assertEqual(status, 201)
        locacao_id = locacao['id']
        self.locacoes.append(locacao_id)
        self.assertFalse(self.disponivel(filme_id))

        self.assertEqual(self.nova_locacao(filme_id)[0], 409)

        status, consultada = self.request('GET', f'/locacoes/{locacao_id}')
        self.assertEqual((status, consultada['status']), (200, 'Em aberto'))

        status, ativas = self.request('GET', '/locacoes?situacao=ativas')
        self.assertIn(locacao_id, [item['id'] for item in ativas])

        status, _ = self.request('DELETE', f'/locacoes/{locacao_id}')
        self.assertEqual(status, 409)

        status, editada = self.request(
            'PUT',
            f'/locacoes/{locacao_id}',
            {
                'filme_id': filme_id,
                'cliente_nome': 'Outro cliente',
                'data_devolucao_prevista': self.FUTURO,
            },
        )
        self.assertEqual((status, editada['cliente_nome']), (200, 'Outro cliente'))

        status, devolvida = self.request(
            'POST', f'/locacoes/{locacao_id}/devolucao', {}
        )
        self.assertEqual((status, devolvida['status']), (200, 'Devolvido'))
        self.assertTrue(self.disponivel(filme_id))
        self.assertEqual(
            self.request('POST', f'/locacoes/{locacao_id}/devolucao', {})[0], 409
        )

        self.assertEqual(self.request('DELETE', f'/locacoes/{locacao_id}')[0], 204)
        self.locacoes.remove(locacao_id)
        self.assertEqual(self.request('GET', f'/locacoes/{locacao_id}')[0], 404)

    def test_troca_de_filme_atualiza_disponibilidade(self):
        antigo = self.novo_filme()
        novo = self.novo_filme()
        _, locacao = self.nova_locacao(antigo)
        self.locacoes.append(locacao['id'])

        status, editada = self.request(
            'PUT',
            f"/locacoes/{locacao['id']}",
            {
                'filme_id': novo,
                'cliente_nome': 'Cliente integracao',
                'data_devolucao_prevista': self.FUTURO,
            },
        )

        self.assertEqual((status, editada['filme_id']), (200, novo))
        self.assertTrue(self.disponivel(antigo))
        self.assertFalse(self.disponivel(novo))

    def test_filme_com_historico_nao_pode_ser_excluido(self):
        filme_id = self.novo_filme()
        _, locacao = self.nova_locacao(filme_id)
        self.locacoes.append(locacao['id'])
        self.request('POST', f"/locacoes/{locacao['id']}/devolucao", {})

        status, erro = self.request('DELETE', f'/filmes/{filme_id}')

        self.assertEqual(status, 409)
        self.assertIn('locacoes', erro['detail'])

    def test_locacoes_simultaneas_do_mesmo_filme_so_uma_vence(self):
        filme_id = self.novo_filme()
        tentativas = 8
        barreira = threading.Barrier(tentativas)
        resultados = []

        def alugar(indice):
            barreira.wait()
            resultados.append(self.nova_locacao(filme_id, f'Cliente {indice}'))

        threads = [
            threading.Thread(target=alugar, args=(i,)) for i in range(tentativas)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        codigos = sorted(status for status, _ in resultados)
        self.assertEqual(codigos, [201] + [409] * (tentativas - 1))
        for status, corpo in resultados:
            if status == 201:
                self.locacoes.append(corpo['id'])
        self.assertFalse(self.disponivel(filme_id))
        ativas = self.request('GET', '/locacoes?situacao=ativas')[1]
        self.assertEqual(
            len([item for item in ativas if item['filme_id'] == filme_id]), 1
        )


if __name__ == '__main__':
    unittest.main()