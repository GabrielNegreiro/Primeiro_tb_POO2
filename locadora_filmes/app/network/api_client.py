import os
from typing import Any, Optional

import httpx


DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'


class ApiClientError(RuntimeError):
    """Erro seguro e apresentavel ocorrido na comunicacao com a API."""


class ApiCommunicationError(ApiClientError):
    """Indica que nao foi possivel estabelecer comunicacao com a API."""


class ApiTimeoutError(ApiClientError):
    """Indica que a API excedeu o tempo limite configurado."""


class ApiInvalidResponseError(ApiClientError):
    """Indica uma resposta que nao respeita o contrato JSON esperado."""


class ApiSerializationError(ApiClientError):
    """Indica que os dados da requisicao nao puderam ser serializados."""


class ApiHttpError(ApiClientError):
    """Representa uma resposta HTTP de erro sem expor detalhes internos."""

    MENSAGENS = {
        404: 'Filme nao encontrado.',
        409: 'Operacao impedida por uma regra de negocio.',
        422: 'Os dados informados sao invalidos.',
        500: 'O servico encontrou um erro interno.',
        503: 'O servico esta temporariamente indisponivel.',
    }

    def __init__(self, status_code: int, detail=None, mensagem=None):
        """Inicializa com status, detalhe interno opcional e mensagem publica."""
        self.status_code = status_code
        # O detalhe nunca entra na mensagem; so os modulos que conhecem os
        # textos seguros do proprio backend podem decidir usa-lo.
        self.detail = detail if isinstance(detail, str) else None
        texto = mensagem or self.MENSAGENS.get(
            status_code,
            f'A API recusou a operacao (HTTP {status_code}).',
        )
        super().__init__(texto)


class ApiClient:
    """Cliente HTTP reutilizavel, independente de Qt e do backend."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        connect_timeout: float = 3.0,
        read_timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        """Configura URL, timeouts e transporte HTTP opcional para testes."""
        configurada = base_url or os.getenv(
            'LOCADORA_API_BASE_URL',
            DEFAULT_API_BASE_URL,
        )
        configurada = configurada.strip().rstrip('/')
        if not configurada:
            raise ValueError('A URL da API nao pode ser vazia.')

        self.base_url = configurada
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            transport=transport,
            headers={'Accept': 'application/json'},
        )

    def get(self, path: str, *, params: Optional[dict] = None) -> Any:
        """Executa GET e retorna o JSON decodificado."""
        return self._request('GET', path, params=params)

    def post(self, path: str, *, json: dict) -> Any:
        """Executa POST com um corpo JSON."""
        return self._request('POST', path, json=json)

    def put(self, path: str, *, json: dict) -> Any:
        """Executa PUT com um corpo JSON."""
        return self._request('PUT', path, json=json)

    def delete(self, path: str) -> None:
        """Executa DELETE e aceita uma resposta sem conteudo."""
        self._request('DELETE', path)

    def close(self) -> None:
        """Libera conexoes mantidas pelo pool do httpx."""
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        """Centraliza transporte, erros HTTP e decodificacao JSON."""
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise ApiTimeoutError(
                'Nao foi possivel concluir a comunicacao no tempo esperado.'
            ) from error
        except httpx.RequestError as error:
            raise ApiCommunicationError(
                'Nao foi possivel conectar ao servico de filmes.'
            ) from error
        except (TypeError, ValueError) as error:
            raise ApiSerializationError(
                'Nao foi possivel preparar os dados para envio.'
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise ApiHttpError(response.status_code, self._detalhe(response))
        if response.status_code == 204:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise ApiInvalidResponseError(
                'A API retornou uma resposta JSON invalida.'
            ) from error

    @staticmethod
    def _detalhe(response) -> Optional[Any]:
        """Extrai o campo detail de um erro JSON, sem falhar se nao existir."""
        try:
            corpo = response.json()
        except ValueError:
            return None
        if isinstance(corpo, dict):
            return corpo.get('detail')
        return None