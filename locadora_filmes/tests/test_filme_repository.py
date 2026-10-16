import json
import tempfile
import unittest
from pathlib import Path

from app.data.filme_repository import FilmeRepository
from app.models.filme import Filme


class FilmeRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.diretorio_temporario = tempfile.TemporaryDirectory()
        self.caminho_arquivo = (
            Path(self.diretorio_temporario.name) / 'dados' / 'filmes.json'
        )
        self.repository = FilmeRepository(self.caminho_arquivo)

    def tearDown(self):
        self.diretorio_temporario.cleanup()

    def test_carregar_quando_arquivo_nao_existe(self):
        self.assertEqual(self.repository.carregar_filmes(), [])

    def test_salvar_cria_arquivo_json_legivel_em_utf8(self):
        filmes = [
            Filme(1, 'João e Maria', 'Animação', 2020, 95, True),
        ]

        self.repository.salvar_filmes(filmes)

        self.assertTrue(self.caminho_arquivo.exists())
        conteudo = self.caminho_arquivo.read_text(encoding='utf-8')
        self.assertIn('João e Maria', conteudo)
        self.assertIn('\n    {', conteudo)
        self.assertEqual(json.loads(conteudo)[0]['genero'], 'Animação')

    def test_carregar_reconstroi_filmes_e_preserva_valores(self):
        filmes = [
            Filme(1, 'Interestelar', 'Ficção científica', 2014, 169, True),
            Filme(2, 'Cidade de Deus', 'Drama', 2002, 130, False),
        ]
        self.repository.salvar_filmes(filmes)

        carregados = self.repository.carregar_filmes()

        self.assertEqual(len(carregados), 2)
        self.assertTrue(all(isinstance(filme, Filme) for filme in carregados))
        self.assertEqual(carregados, filmes)
        self.assertFalse(carregados[1].disponivel)

    def test_salvar_e_carregar_lista_vazia(self):
        self.repository.salvar_filmes([])

        self.assertTrue(self.caminho_arquivo.exists())
        self.assertEqual(self.repository.carregar_filmes(), [])

    def test_carregar_arquivo_vazio(self):
        self.caminho_arquivo.parent.mkdir(parents=True)
        self.caminho_arquivo.write_text('', encoding='utf-8')

        self.assertEqual(self.repository.carregar_filmes(), [])

    def test_json_invalido_gera_erro_explicito(self):
        self.caminho_arquivo.parent.mkdir(parents=True)
        self.caminho_arquivo.write_text('{invalido', encoding='utf-8')

        with self.assertRaisesRegex(ValueError, 'Arquivo JSON invalido'):
            self.repository.carregar_filmes()


if __name__ == '__main__':
    unittest.main()
