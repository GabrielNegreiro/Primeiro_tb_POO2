import unittest
from unittest.mock import Mock

from app.models.filme import Filme
from app.network.api_client import ApiClient, ApiInvalidResponseError
from app.services.filme_api_service import (
    FilmeApiService,
    OperacaoFilmeBloqueadaError,
)


def registro_filme(
    filme_id=1,
    titulo='Matrix',
    genero='Ficcao',
    ano=1999,
    duracao=136,
    disponivel=True,
):
    return {
        'id': filme_id,
        'titulo': titulo,
        'genero': genero,
        'ano': ano,
        'duracao': duracao,
        'disponivel': disponivel,
    }


class FilmeApiServiceTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock(spec=ApiClient)
        self.service = FilmeApiService(self.client)

    def test_get_converte_json_e_envia_filtros(self):
        self.client.get.return_value = [registro_filme()]

        filmes = self.service.carregar_filmes('matrix', True)

        self.client.get.assert_called_once_with(
            '/filmes',
            params={'titulo': 'matrix', 'disponivel': 'true'},
        )
        self.assertEqual(filmes, [Filme(1, 'Matrix', 'Ficcao', 1999, 136, True)])

    def test_post_put_delete_e_cache(self):
        self.client.post.return_value = registro_filme()
        criado = self.service.adicionar_filme(
            'Matrix', 'Ficcao', 1999, 136, True
        )
        self.assertIs(self.service.obter_filme(1), criado)

        self.client.get.return_value = registro_filme()
        self.client.put.return_value = registro_filme(
            titulo='Matrix Reloaded',
            ano=2003,
            duracao=138,
        )
        atualizado = self.service.atualizar_filme(
            1,
            'Matrix Reloaded',
            'Ficcao',
            2003,
            138,
            False,
        )
        self.assertEqual(atualizado.titulo, 'Matrix Reloaded')
        self.client.get.assert_called_once_with('/filmes/1')
        corpo_put = self.client.put.call_args.kwargs['json']
        self.assertTrue(
            corpo_put['disponivel'],
            'A edicao cadastral deve preservar a disponibilidade atual.',
        )

        removido = self.service.remover_filme(1)
        self.client.delete.assert_called_once_with('/filmes/1')
        self.assertEqual(removido.id, 1)
        self.assertEqual(self.service.listar_filmes(), [])

    def test_busca_por_id_utiliza_endpoint_e_atualiza_cache(self):
        self.client.get.return_value = registro_filme(7, 'Interestelar')

        filme = self.service.buscar_por_id(7)

        self.client.get.assert_called_once_with('/filmes/7')
        self.assertIs(self.service.obter_filme(7), filme)

    def test_pesquisa_local_preserva_titulo_genero_e_ano(self):
        self.service.aplicar_filmes_carregados([
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'Toy Story', 'Animacao', 1995, 81, False),
        ])

        self.assertEqual(self.service.buscar_filmes('toy')[0].id, 2)
        self.assertEqual(self.service.buscar_filmes('ficcao')[0].id, 1)
        self.assertEqual(self.service.buscar_filmes('1995')[0].id, 2)
        self.assertEqual([f.id for f in self.service.listar_disponiveis()], [1])
        self.client.get.assert_not_called()

    def test_postgresql_vazio_permanece_vazio_sem_fallback(self):
        self.client.get.return_value = []

        self.assertEqual(self.service.carregar_filmes(), [])
        self.assertEqual(self.service.listar_filmes(), [])

    def test_resposta_com_estrutura_invalida_falha_sem_apagar_cache(self):
        original = Filme(1, 'Matrix', 'Ficcao', 1999, 136, True)
        self.service.aplicar_filmes_carregados([original])
        self.client.get.return_value = [{'id': 2}]

        with self.assertRaises(ApiInvalidResponseError):
            self.service.carregar_filmes()

        self.assertEqual(self.service.listar_filmes(), [original])

    def test_falha_no_delete_preserva_cache(self):
        filme = Filme(1, 'Matrix', 'Ficcao', 1999, 136, True)
        self.service.aplicar_filmes_carregados([filme])
        self.client.delete.side_effect = RuntimeError('conflito')

        with self.assertRaises(RuntimeError):
            self.service.remover_filme(1)

        self.assertEqual(self.service.listar_filmes(), [filme])

    def test_locacao_local_nao_pode_alterar_disponibilidade(self):
        with self.assertRaisesRegex(
            OperacaoFilmeBloqueadaError,
            'API de locacoes',
        ):
            self.service.definir_disponibilidade(1, False)


if __name__ == '__main__':
    unittest.main()
