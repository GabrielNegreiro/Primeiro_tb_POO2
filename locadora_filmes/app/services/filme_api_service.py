from typing import Iterable, Optional

from app.models.filme import Filme
from app.network.api_client import ApiClient, ApiInvalidResponseError


class OperacaoFilmeBloqueadaError(RuntimeError):
    """Indica uma operacao indisponivel durante a integracao temporaria."""


class FilmeApiService:
    """Adapta a API REST de filmes aos contratos usados pelo desktop."""

    def __init__(self, api_client: ApiClient):
        """Inicializa o adapter com cache vazio e cliente HTTP injetado."""
        self.api_client = api_client
        self.filmes: list[Filme] = []

    def carregar_filmes(
        self,
        titulo: Optional[str] = None,
        disponivel: Optional[bool] = None,
    ) -> list[Filme]:
        """Consulta GET /filmes e substitui o cache apenas apos sucesso."""
        params = {}
        if titulo:
            params['titulo'] = titulo
        if disponivel is not None:
            params['disponivel'] = str(disponivel).lower()

        resposta = self.api_client.get('/filmes', params=params or None)
        if not isinstance(resposta, list):
            raise ApiInvalidResponseError(
                'A API retornou uma lista de filmes invalida.'
            )
        filmes = [self._converter_filme(item) for item in resposta]
        self.aplicar_filmes_carregados(filmes)
        return self.listar_filmes()

    def aplicar_filmes_carregados(self, filmes: Iterable[Filme]) -> None:
        """Atualiza o cache inclusive quando o PostgreSQL esta vazio."""
        self.filmes = list(filmes)

    def listar_filmes(self) -> list[Filme]:
        """Retorna uma copia do ultimo acervo confirmado pela API."""
        return list(self.filmes)

    def buscar_filmes(self, texto: str) -> list[Filme]:
        """Filtra localmente titulo, genero e ano sem novas requisicoes."""
        termo = texto.strip().lower()
        if not termo:
            return self.listar_filmes()
        return [
            filme
            for filme in self.filmes
            if termo in filme.titulo.lower()
            or termo in filme.genero.lower()
            or termo in str(filme.ano)
        ]

    def buscar_por_id(self, filme_id: int) -> Filme:
        """Consulta GET /filmes/{id} e atualiza o item no cache."""
        resposta = self.api_client.get(f'/filmes/{int(filme_id)}')
        filme = self._converter_filme(resposta)
        self._atualizar_cache(filme)
        return filme

    def obter_filme(self, filme_id: int) -> Optional[Filme]:
        """Busca no cache sem bloquear a thread grafica."""
        return next(
            (filme for filme in self.filmes if filme.id == int(filme_id)),
            None,
        )

    def adicionar_filme(
        self,
        titulo,
        genero,
        ano,
        duracao,
        disponivel=True,
    ) -> Filme:
        """Cadastra via POST e inclui no cache o objeto confirmado."""
        resposta = self.api_client.post(
            '/filmes',
            json=self._dados_filme(
                titulo,
                genero,
                ano,
                duracao,
                bool(disponivel),
            ),
        )
        filme = self._converter_filme(resposta)
        self._atualizar_cache(filme)
        return filme

    def atualizar_filme(
        self,
        id,
        titulo,
        genero,
        ano,
        duracao,
        disponivel=None,
    ) -> Filme:
        """Atualiza cadastro via PUT preservando a disponibilidade atual."""
        # Rele o recurso dentro do worker para nao enviar um estado antigo do
        # cache. A API continua sendo a fonte da disponibilidade.
        filme_atual = self.buscar_por_id(int(id))

        resposta = self.api_client.put(
            f'/filmes/{int(id)}',
            json=self._dados_filme(
                titulo,
                genero,
                ano,
                duracao,
                filme_atual.disponivel,
            ),
        )
        filme = self._converter_filme(resposta)
        self._atualizar_cache(filme)
        return filme

    def remover_filme(self, id) -> Filme:
        """Exclui via DELETE e somente entao remove o item do cache."""
        filme = self.obter_filme(int(id))
        if filme is None:
            filme = self.buscar_por_id(int(id))
        self.api_client.delete(f'/filmes/{int(id)}')
        self.filmes = [item for item in self.filmes if item.id != int(id)]
        return filme

    def listar_disponiveis(self) -> list[Filme]:
        """Retorna do cache somente filmes marcados como disponiveis."""
        return [filme for filme in self.filmes if filme.disponivel]

    def definir_disponibilidade(self, filme_id: int, disponivel: bool) -> Filme:
        """Bloqueia alteracoes vindas do modulo local de locacoes."""
        raise OperacaoFilmeBloqueadaError(
            'A disponibilidade deve ser alterada pela API de locacoes. '
            'A integracao desse modulo ainda esta pendente.'
        )

    def fechar(self) -> None:
        """Encerra o cliente HTTP quando a janela principal termina."""
        self.api_client.close()

    @staticmethod
    def _dados_filme(
        titulo,
        genero,
        ano,
        duracao,
        disponivel,
    ) -> dict:
        """Normaliza o corpo JSON aceito pela API."""
        return {
            'titulo': str(titulo).strip(),
            'genero': str(genero).strip(),
            'ano': int(ano),
            'duracao': int(duracao),
            'disponivel': bool(disponivel),
        }

    @staticmethod
    def _converter_filme(registro) -> Filme:
        """Valida minimamente e converte JSON em Filme do desktop."""
        if not isinstance(registro, dict):
            raise ApiInvalidResponseError(
                'A API retornou um filme em formato invalido.'
            )

        obrigatorios = {
            'id',
            'titulo',
            'genero',
            'ano',
            'duracao',
            'disponivel',
        }
        if not obrigatorios.issubset(registro):
            raise ApiInvalidResponseError(
                'A resposta da API nao possui todos os campos do filme.'
            )

        id_valido = isinstance(registro['id'], int) and not isinstance(
            registro['id'], bool
        )
        ano_valido = isinstance(registro['ano'], int) and not isinstance(
            registro['ano'], bool
        )
        duracao_valida = isinstance(
            registro['duracao'], int
        ) and not isinstance(registro['duracao'], bool)
        if (
            not id_valido
            or registro['id'] <= 0
            or not isinstance(registro['titulo'], str)
            or not registro['titulo'].strip()
            or not isinstance(registro['genero'], str)
            or not registro['genero'].strip()
            or not ano_valido
            or not duracao_valida
            or registro['duracao'] <= 0
            or not isinstance(registro['disponivel'], bool)
        ):
            raise ApiInvalidResponseError(
                'A API retornou dados invalidos para um filme.'
            )

        return Filme(
            id=registro['id'],
            titulo=registro['titulo'].strip(),
            genero=registro['genero'].strip(),
            ano=registro['ano'],
            duracao=registro['duracao'],
            disponivel=registro['disponivel'],
        )

    def _atualizar_cache(self, filme: Filme) -> None:
        """Inclui ou substitui um filme preservando ordenacao por ID."""
        self.filmes = [item for item in self.filmes if item.id != filme.id]
        self.filmes.append(filme)
        self.filmes.sort(key=lambda item: item.id)
