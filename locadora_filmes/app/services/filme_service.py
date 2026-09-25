from app.models.filme import Filme


class FilmeService:
    def __init__(self, filmes=None):
        self.filmes = list(filmes) if filmes is not None else self._filmes_iniciais()
        self._proximo_id = self._calcular_proximo_id()

    def listar_filmes(self):
        return list(self.filmes)

    def buscar_filmes(self, texto):
        termo = texto.strip().lower()
        if not termo:
            return self.listar_filmes()

        return [
            filme for filme in self.filmes
            if termo in filme.titulo.lower()
            or termo in filme.genero.lower()
            or termo in str(filme.ano)
        ]

    def obter_filme(self, id):
        for filme in self.filmes:
            if filme.id == id:
                return filme
        return None

    def adicionar_filme(self, titulo, genero, ano, duracao, disponivel=True):
        filme = Filme(
            id=self._proximo_id,
            titulo=titulo.strip(),
            genero=genero.strip(),
            ano=int(ano),
            duracao=int(duracao),
            disponivel=bool(disponivel),
        )
        self.filmes.append(filme)
        self._proximo_id += 1
        return filme

    def atualizar_filme(self, id, titulo, genero, ano, duracao, disponivel):
        filme = self.obter_filme(id)
        if filme is None:
            raise ValueError('Filme nao encontrado.')

        filme.titulo = titulo.strip()
        filme.genero = genero.strip()
        filme.ano = int(ano)
        filme.duracao = int(duracao)
        filme.disponivel = bool(disponivel)
        return filme

    def remover_filme(self, id):
        filme = self.obter_filme(id)
        if filme is None:
            raise ValueError('Filme nao encontrado.')
        if not filme.disponivel:
            raise ValueError('Nao e possivel excluir um filme alugado.')

        self.filmes.remove(filme)
        return filme

    def listar_disponiveis(self):
        return [filme for filme in self.filmes if filme.disponivel]

    def _calcular_proximo_id(self):
        if not self.filmes:
            return 1
        return max(filme.id for filme in self.filmes) + 1

    def _filmes_iniciais(self):
        return [
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'O Poderoso Chefao', 'Drama', 1972, 175, True),
            Filme(3, 'Toy Story', 'Animacao', 1995, 81, True),
            Filme(4, 'Cidade de Deus', 'Drama', 2002, 130, True),
        ]
