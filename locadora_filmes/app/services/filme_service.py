from typing import Iterable, Optional

from app.data.filme_repository import FilmeRepository
from app.models.filme import Filme


class FilmeService:
    def __init__(self, repository=None, filmes=None, carregar_ao_iniciar=True):
        # Mantem compatibilidade com o uso antigo: FilmeService(lista_de_filmes).
        if repository is not None and not hasattr(repository, 'carregar_filmes'):
            if filmes is not None:
                raise TypeError('Informe repository ou filmes, nao ambos.')
            filmes = repository
            repository = None

        self.repository = repository or FilmeRepository()

        if filmes is not None:
            self.filmes = list(filmes)
        elif carregar_ao_iniciar:
            carregados = self.repository.carregar_filmes()
            self.filmes = carregados if carregados else self._filmes_iniciais()
        else:
            self.filmes = []

        self._proximo_id = self._calcular_proximo_id()

    def aplicar_filmes_carregados(self, filmes: Iterable[Filme]) -> None:
        filmes = list(filmes)
        self.filmes = filmes if filmes else self._filmes_iniciais()
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

    def buscar_por_id(self, filme_id: int) -> Optional[Filme]:
        for filme in self.filmes:
            if filme.id == filme_id:
                return filme
        return None

    def obter_filme(self, id):
        return self.buscar_por_id(id)

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
        self._persistir()
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
        self._persistir()
        return filme

    def remover_filme(self, id):
        filme = self.obter_filme(id)
        if filme is None:
            raise ValueError('Filme nao encontrado.')
        if not filme.disponivel:
            raise ValueError('Nao e possivel excluir um filme alugado.')

        self.filmes.remove(filme)
        self._persistir()
        return filme

    def listar_disponiveis(self):
        return [filme for filme in self.filmes if filme.disponivel]

    def _calcular_proximo_id(self):
        if not self.filmes:
            return 1
        return max(filme.id for filme in self.filmes) + 1

    def _persistir(self):
        self.repository.salvar_filmes(self.filmes)

    def _filmes_iniciais(self):
        return [
            Filme(1, 'Matrix', 'Ficcao', 1999, 136, True),
            Filme(2, 'O Poderoso Chefao', 'Drama', 1972, 175, True),
            Filme(3, 'Toy Story', 'Animacao', 1995, 81, True),
            Filme(4, 'Cidade de Deus', 'Drama', 2002, 130, True),
        ]
