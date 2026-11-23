from datetime import date, timedelta
from typing import Callable, Iterable, Optional

from app.models.locacao_api import LocacaoApi
from app.network.api_client import (
    ApiClient,
    ApiCommunicationError,
    ApiHttpError,
    ApiInvalidResponseError,
)

SITUACOES = ('todas', 'ativas', 'atrasadas')

_MENSAGENS_PADRAO = {
    404: 'Locacao ou filme nao encontrado.',
    409: 'A operacao nao e permitida no estado atual da locacao ou do filme.',
    422: 'Os dados informados sao invalidos.',
}


class LocacaoApiService:
    """Adapta a API REST de locacoes aos contratos usados pelo desktop."""

    assincrono = True

    def __init__(
        self,
        api_client: ApiClient,
        filme_service,
        hoje: Callable[[], date] = date.today,
    ):
        """Inicializa com cache vazio, cliente HTTP e servico de filmes."""
        self.api_client = api_client
        self.filme_service = filme_service
        self.hoje = hoje
        self.locacoes: list[LocacaoApi] = []
        self.carregado = False

    # --- consultas -----------------------------------------------------

    def carregar_locacoes(self) -> list[LocacaoApi]:
        """Consulta GET /locacoes e substitui o cache apenas apos sucesso."""
        locacoes = self._consultar('todas')
        self.aplicar_locacoes_carregadas(locacoes)
        return self.listar_todas()

    def consultar_situacao(self, situacao: str) -> list[LocacaoApi]:
        """Consulta GET /locacoes?situacao=... sem alterar o cache."""
        return [self._com_filme(item) for item in self._consultar(situacao)]

    def aplicar_locacoes_carregadas(
        self, locacoes: Iterable[LocacaoApi]
    ) -> None:
        """Atualiza o cache inclusive quando o PostgreSQL esta vazio."""
        self.locacoes = list(locacoes)
        self.carregado = True

    def buscar_por_id(self, locacao_id) -> LocacaoApi:
        """Consulta GET /locacoes/{id} e atualiza o item no cache."""
        identificador = self._id_locacao(locacao_id)
        resposta = self._executar(
            self.api_client.get, f'/locacoes/{identificador}'
        )
        locacao = self._converter_locacao(resposta)
        self._atualizar_cache(locacao)
        return self._com_filme(locacao)

    def obter_locacao(self, locacao_id) -> Optional[LocacaoApi]:
        """Busca no cache, sem rede, usando o ID estavel da locacao."""
        identificador = self._id_locacao(locacao_id)
        locacao = next(
            (item for item in self.locacoes if item.id == identificador),
            None,
        )
        return self._com_filme(locacao) if locacao is not None else None

    def listar_todas(self) -> list[LocacaoApi]:
        """Retorna do cache todas as locacoes confirmadas pela API."""
        return [self._com_filme(item) for item in self.locacoes]

    def listar_ativas(self) -> list[LocacaoApi]:
        """Retorna do cache as locacoes em aberto."""
        return [item for item in self.listar_todas() if item.status == 'Em aberto']

    def listar_atrasadas(self) -> list[LocacaoApi]:
        """Retorna do cache as locacoes marcadas como atrasadas pela API."""
        return [item for item in self.listar_todas() if item.atrasada]

    # --- operacoes de escrita (executar em worker) ---------------------

    def criar_locacao(
        self,
        filme,
        cliente_nome,
        dias_previstos=7,
        data_locacao: Optional[date] = None,
    ) -> LocacaoApi:
        """Cadastra via POST; o cache so recebe o objeto confirmado."""
        nome = self._validar_nome(cliente_nome)
        dias = self._validar_dias(dias_previstos)
        inicio = data_locacao or self.hoje()
        corpo = {
            'filme_id': self._id_filme(filme),
            'cliente_nome': nome,
            'data_locacao': inicio.isoformat(),
            'data_devolucao_prevista': (
                inicio + timedelta(days=dias)
            ).isoformat(),
        }
        resposta = self._executar(self.api_client.post, '/locacoes', json=corpo)
        locacao = self._converter_locacao(resposta)
        self._atualizar_cache(locacao)
        return self._com_filme(locacao)

    def atualizar_locacao(
        self, locacao, filme, cliente_nome, dias_previstos
    ) -> LocacaoApi:
        """Edita via PUT; o prazo conta a partir da data original da locacao."""
        identificador = self._id_locacao(locacao)
        nome = self._validar_nome(cliente_nome)
        dias = self._validar_dias(dias_previstos)
        atual = self.obter_locacao(identificador)
        if atual is None:
            atual = self.buscar_por_id(identificador)
        corpo = {
            'filme_id': self._id_filme(filme),
            'cliente_nome': nome,
            'data_devolucao_prevista': (
                atual.data_locacao + timedelta(days=dias)
            ).isoformat(),
        }
        resposta = self._executar(
            self.api_client.put, f'/locacoes/{identificador}', json=corpo
        )
        confirmada = self._converter_locacao(resposta)
        self._atualizar_cache(confirmada)
        return self._com_filme(confirmada)

    def devolver_locacao(self, locacao) -> LocacaoApi:
        """Registra a devolucao via POST; o backend usa a data de hoje."""
        identificador = self._id_locacao(locacao)
        resposta = self._executar(
            self.api_client.post,
            f'/locacoes/{identificador}/devolucao',
            json={},
        )
        confirmada = self._converter_locacao(resposta)
        self._atualizar_cache(confirmada)
        return self._com_filme(confirmada)

    def excluir_locacao(self, locacao) -> Optional[LocacaoApi]:
        """Exclui via DELETE e somente entao remove o item do cache."""
        identificador = self._id_locacao(locacao)
        existente = self.obter_locacao(identificador)
        self._executar(self.api_client.delete, f'/locacoes/{identificador}')
        self.locacoes = [
            item for item in self.locacoes if item.id != identificador
        ]
        return existente

    def atualizar_filmes(self):
        """Recarrega o acervo; a disponibilidade vem sempre da API."""
        return self.filme_service.carregar_filmes()

    # --- internos ------------------------------------------------------

    def _consultar(self, situacao: str) -> list[LocacaoApi]:
        if situacao not in SITUACOES:
            raise ValueError('Situacao de locacao invalida.')
        params = None if situacao == 'todas' else {'situacao': situacao}
        resposta = self._executar(
            self.api_client.get, '/locacoes', params=params
        )
        if not isinstance(resposta, list):
            raise ApiInvalidResponseError(
                'A API retornou uma lista de locacoes invalida.'
            )
        return [self._converter_locacao(item) for item in resposta]

    def _executar(self, metodo, *args, **kwargs):
        """Chama o ApiClient e traduz erros para mensagens de locacoes."""
        try:
            return metodo(*args, **kwargs)
        except ApiHttpError as erro:
            traduzido = self._traduzir_http(erro)
            if traduzido is erro:
                raise
            raise traduzido from erro
        except ApiCommunicationError as erro:
            raise ApiCommunicationError(
                'Nao foi possivel conectar ao servico de locacoes.'
            ) from erro

    @staticmethod
    def _traduzir_http(erro: ApiHttpError) -> ApiHttpError:
        padrao = _MENSAGENS_PADRAO.get(erro.status_code)
        if padrao is None:
            return erro
        detalhe = erro.detail
        # O detalhe vem das regras do proprio backend de locacoes (texto curto
        # e sem dados internos). Textos genericos do FastAPI sao ignorados.
        if (
            detalhe
            and len(detalhe) <= 150
            and detalhe.strip().lower() != 'not found'
        ):
            return ApiHttpError(erro.status_code, mensagem=detalhe.strip())
        return ApiHttpError(erro.status_code, mensagem=padrao)

    def _com_filme(self, locacao: LocacaoApi) -> LocacaoApi:
        """Associa o filme pelo ID, sem inventar dados se ele nao existe."""
        obter = getattr(self.filme_service, 'obter_filme', None)
        locacao.filme = obter(locacao.filme_id) if obter is not None else None
        return locacao

    def _atualizar_cache(self, locacao: LocacaoApi) -> None:
        self.locacoes = [
            item for item in self.locacoes if item.id != locacao.id
        ]
        self.locacoes.append(locacao)
        self.locacoes.sort(key=lambda item: item.id)

    @staticmethod
    def _inteiro_positivo(valor) -> bool:
        return (
            isinstance(valor, int) and not isinstance(valor, bool) and valor > 0
        )

    def _id_locacao(self, locacao) -> int:
        identificador = getattr(locacao, 'id', locacao)
        if not self._inteiro_positivo(identificador):
            raise ValueError('Selecione uma locacao valida.')
        return identificador

    def _id_filme(self, filme) -> int:
        identificador = getattr(filme, 'id', filme)
        if not self._inteiro_positivo(identificador):
            raise ValueError('Selecione um filme valido.')
        return identificador

    @staticmethod
    def _validar_nome(cliente_nome) -> str:
        nome = str(cliente_nome).strip()
        if not nome:
            raise ValueError('Informe o nome do cliente.')
        return nome

    def _validar_dias(self, dias_previstos) -> int:
        if not self._inteiro_positivo(dias_previstos):
            raise ValueError('O prazo deve ter pelo menos um dia.')
        return dias_previstos

    @staticmethod
    def _converter_data(valor, obrigatoria=True) -> Optional[date]:
        if valor is None and not obrigatoria:
            return None
        if not isinstance(valor, str):
            raise ApiInvalidResponseError(
                'A API retornou uma data de locacao invalida.'
            )
        try:
            return date.fromisoformat(valor)
        except ValueError as erro:
            raise ApiInvalidResponseError(
                'A API retornou uma data de locacao invalida.'
            ) from erro

    @classmethod
    def _converter_locacao(cls, registro) -> LocacaoApi:
        """Valida o JSON e converte em LocacaoApi do desktop."""
        if not isinstance(registro, dict):
            raise ApiInvalidResponseError(
                'A API retornou uma locacao em formato invalido.'
            )
        obrigatorios = {
            'id',
            'filme_id',
            'cliente_nome',
            'data_locacao',
            'data_devolucao_prevista',
            'data_devolucao_real',
            'status',
            'atrasada',
        }
        if not obrigatorios.issubset(registro):
            raise ApiInvalidResponseError(
                'A resposta da API nao possui todos os campos da locacao.'
            )
        if (
            not cls._inteiro_positivo(registro['id'])
            or not cls._inteiro_positivo(registro['filme_id'])
            or not isinstance(registro['cliente_nome'], str)
            or not registro['cliente_nome'].strip()
            or registro['status'] not in ('Em aberto', 'Devolvido')
            or not isinstance(registro['atrasada'], bool)
        ):
            raise ApiInvalidResponseError(
                'A API retornou dados invalidos para uma locacao.'
            )
        return LocacaoApi(
            id=registro['id'],
            filme_id=registro['filme_id'],
            cliente_nome=registro['cliente_nome'].strip(),
            data_locacao=cls._converter_data(registro['data_locacao']),
            data_devolucao_prevista=cls._converter_data(
                registro['data_devolucao_prevista']
            ),
            data_devolucao_real=cls._converter_data(
                registro['data_devolucao_real'], obrigatoria=False
            ),
            status=registro['status'],
            atrasada=registro['atrasada'],
        )