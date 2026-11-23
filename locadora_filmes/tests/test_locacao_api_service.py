import json
import unittest
from datetime import date

import httpx

from app.models.filme import Filme
from app.network.api_client import (
    ApiClient,
    ApiCommunicationError,
    ApiHttpError,
    ApiInvalidResponseError,
    ApiTimeoutError,
)
from app.services.locacao_api_service import LocacaoApiService


def registro(**alteracoes):
    dados = {
        'id': 1,
        'filme_id': 1,
        'cliente_nome': 'Ana',
        'data_locacao': '2026-11-22',
        'data_devolucao_prevista': '2026-11-29',
        'data_devolucao_real': None,
        'status': 'Em aberto',
        'atrasada': False,
    }
    dados.update(alteracoes)
    return dados


def filme(id=1, disponivel=True):
    return Filme(
        id=id,
        titulo=f'Filme {id}',
        genero='Ficcao',
        ano=1999,
        duracao=100,
        disponivel=disponivel,
    )


class FilmesFalsos:
    def __init__(self, filmes=()):
        self.filmes = list(filmes)
        self.carregamentos = 0

    def obter_filme(self, filme_id):
        return next((f for f in self.filmes if f.id == filme_id), None)

    def carregar_filmes(self):
        self.carregamentos += 1
        return list(self.filmes)


class LocacaoApiServiceTest(unittest.TestCase):
    def criar_servico(self, handler, filmes=()):
        cliente = ApiClient(
            'http://api.test', transport=httpx.MockTransport(handler)
        )
        self.addCleanup(cliente.close)
        self.filmes = FilmesFalsos(filmes)
        return LocacaoApiService(
            cliente, self.filmes, hoje=lambda: date(2026, 11, 22)
        )

    def test_carregar_converte_datas_e_associa_filme_pelo_id(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(
                200,
                json=[registro(id=2, filme_id=7, data_devolucao_real=None)],
            ),
            filmes=[filme(7)],
        )

        locacoes = servico.carregar_locacoes()

        self.assertEqual(locacoes[0].data_locacao, date(2026, 11, 22))
        self.assertEqual(locacoes[0].data_devolucao_prevista, date(2026, 11, 29))
        self.assertIsNone(locacoes[0].data_devolucao_real)
        self.assertEqual(locacoes[0].filme.id, 7)
        self.assertEqual(locacoes[0].titulo_filme, 'Filme 7')

    def test_filme_fora_do_cache_nao_e_inventado(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(200, json=[registro(filme_id=9)])
        )

        locacao = servico.carregar_locacoes()[0]

        self.assertIsNone(locacao.filme)
        self.assertIn('#9', locacao.titulo_filme)
        self.assertEqual(len(servico.listar_todas()), 1)

    def test_listas_de_ativas_e_atrasadas_usam_o_cache(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(
                200,
                json=[
                    registro(id=1),
                    registro(id=2, atrasada=True),
                    registro(
                        id=3,
                        status='Devolvido',
                        data_devolucao_real='2026-11-23',
                    ),
                ],
            )
        )
        servico.carregar_locacoes()

        self.assertEqual([l.id for l in servico.listar_ativas()], [1, 2])
        self.assertEqual([l.id for l in servico.listar_atrasadas()], [2])

    def test_consultar_situacao_envia_parametro_e_nao_altera_cache(self):
        urls = []

        def handler(request):
            urls.append(str(request.url))
            return httpx.Response(200, json=[registro(id=4)])

        servico = self.criar_servico(handler)

        locacoes = servico.consultar_situacao('atrasadas')

        self.assertIn('situacao=atrasadas', urls[0])
        self.assertEqual(locacoes[0].id, 4)
        self.assertEqual(servico.listar_todas(), [])
        with self.assertRaises(ValueError):
            servico.consultar_situacao('qualquer')

    def test_criar_envia_corpo_e_atualiza_cache_apos_sucesso(self):
        corpos = []

        def handler(request):
            corpos.append(json.loads(request.content))
            return httpx.Response(201, json=registro(id=5))

        servico = self.criar_servico(handler, filmes=[filme(1)])

        locacao = servico.criar_locacao(filme(1), ' Ana ', dias_previstos=7)

        self.assertEqual(
            corpos[0],
            {
                'filme_id': 1,
                'cliente_nome': 'Ana',
                'data_locacao': '2026-11-22',
                'data_devolucao_prevista': '2026-11-29',
            },
        )
        self.assertEqual(locacao.id, 5)
        self.assertEqual([l.id for l in servico.listar_todas()], [5])

    def test_criar_com_409_mostra_mensagem_do_backend_e_nao_altera_cache(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(
                409, json={'detail': 'Filme indisponivel para locacao.'}
            )
        )

        with self.assertRaises(ApiHttpError) as contexto:
            servico.criar_locacao(filme(1), 'Ana')

        self.assertEqual(contexto.exception.status_code, 409)
        self.assertEqual(
            str(contexto.exception), 'Filme indisponivel para locacao.'
        )
        self.assertEqual(servico.listar_todas(), [])

    def test_editar_conta_o_prazo_da_data_original(self):
        corpos = []

        def handler(request):
            if request.method == 'GET':
                return httpx.Response(
                    200,
                    json=[
                        registro(
                            id=3,
                            data_locacao='2026-11-01',
                            data_devolucao_prevista='2026-11-08',
                        )
                    ],
                )
            corpos.append(json.loads(request.content))
            return httpx.Response(
                200,
                json=registro(
                    id=3,
                    cliente_nome='Bia',
                    data_locacao='2026-11-01',
                    data_devolucao_prevista='2026-11-11',
                ),
            )

        servico = self.criar_servico(handler, filmes=[filme(1)])
        servico.carregar_locacoes()

        servico.atualizar_locacao(3, filme(1), 'Bia', 10)

        self.assertEqual(
            corpos[0],
            {
                'filme_id': 1,
                'cliente_nome': 'Bia',
                'data_devolucao_prevista': '2026-11-11',
            },
        )
        self.assertEqual(servico.obter_locacao(3).cliente_nome, 'Bia')

    def test_devolver_envia_corpo_vazio(self):
        recebidas = []

        def handler(request):
            recebidas.append((request.url.path, json.loads(request.content)))
            return httpx.Response(
                200,
                json=registro(
                    id=3,
                    status='Devolvido',
                    data_devolucao_real='2026-11-22',
                ),
            )

        servico = self.criar_servico(handler)

        locacao = servico.devolver_locacao(3)

        self.assertEqual(recebidas, [('/locacoes/3/devolucao', {})])
        self.assertEqual(locacao.status, 'Devolvido')
        self.assertEqual(locacao.data_devolucao_real, date(2026, 11, 22))

    def test_excluir_remove_do_cache_somente_apos_204(self):
        def handler(request):
            if request.method == 'GET':
                return httpx.Response(
                    200,
                    json=[
                        registro(
                            id=3,
                            status='Devolvido',
                            data_devolucao_real='2026-11-23',
                        )
                    ],
                )
            return httpx.Response(204)

        servico = self.criar_servico(handler)
        servico.carregar_locacoes()

        servico.excluir_locacao(3)

        self.assertEqual(servico.listar_todas(), [])

    def test_excluir_com_409_mantem_o_cache(self):
        def handler(request):
            if request.method == 'GET':
                return httpx.Response(200, json=[registro(id=3)])
            return httpx.Response(409, json={'detail': 'x' * 400})

        servico = self.criar_servico(handler)
        servico.carregar_locacoes()

        with self.assertRaises(ApiHttpError) as contexto:
            servico.excluir_locacao(3)

        # Detalhe longo demais e descartado em favor da mensagem padrao.
        self.assertNotIn('xxxx', str(contexto.exception))
        self.assertEqual(len(servico.listar_todas()), 1)

    def test_resposta_invalida_nao_altera_o_cache(self):
        respostas = [[registro(id=1)], [{'id': 2}]]
        servico = self.criar_servico(
            lambda _r: httpx.Response(200, json=respostas.pop(0))
        )
        servico.carregar_locacoes()

        with self.assertRaises(ApiInvalidResponseError):
            servico.carregar_locacoes()

        self.assertEqual([l.id for l in servico.listar_todas()], [1])

    def test_data_invalida_na_resposta_e_rejeitada(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(
                200, json=[registro(data_locacao='22/11/2026')]
            )
        )

        with self.assertRaises(ApiInvalidResponseError):
            servico.carregar_locacoes()

    def test_timeout_e_falha_de_conexao_nao_viram_lista_vazia(self):
        def lento(request):
            raise httpx.ReadTimeout('demorou', request=request)

        def offline(request):
            raise httpx.ConnectError('offline', request=request)

        with self.assertRaises(ApiTimeoutError):
            self.criar_servico(lento).carregar_locacoes()
        with self.assertRaisesRegex(ApiCommunicationError, 'locacoes'):
            self.criar_servico(offline).carregar_locacoes()

    def test_422_e_503_tem_mensagens_seguras(self):
        servico = self.criar_servico(
            lambda _r: httpx.Response(422, json={'detail': [{'loc': ['x']}]})
        )
        with self.assertRaises(ApiHttpError) as contexto:
            servico.criar_locacao(filme(1), 'Ana')
        self.assertEqual(
            str(contexto.exception), 'Os dados informados sao invalidos.'
        )

        servico = self.criar_servico(
            lambda _r: httpx.Response(503, json={'detail': 'senha-do-banco'})
        )
        with self.assertRaises(ApiHttpError) as contexto:
            servico.carregar_locacoes()
        self.assertEqual(contexto.exception.status_code, 503)
        self.assertNotIn('senha-do-banco', str(contexto.exception))

    def test_validacao_local_nao_faz_requisicao(self):
        chamadas = []
        servico = self.criar_servico(
            lambda r: chamadas.append(r) or httpx.Response(201, json={})
        )

        with self.assertRaises(ValueError):
            servico.criar_locacao(filme(1), '   ')
        with self.assertRaises(ValueError):
            servico.criar_locacao(filme(1), 'Ana', dias_previstos=0)
        with self.assertRaises(ValueError):
            servico.criar_locacao(0, 'Ana')

        self.assertEqual(chamadas, [])

    def test_mensagem_padrao_de_filmes_continua_compativel(self):
        self.assertEqual(str(ApiHttpError(404)), 'Filme nao encontrado.')
        self.assertIsNone(ApiHttpError(404, {'x': 1}).detail)


if __name__ == '__main__':
    unittest.main()