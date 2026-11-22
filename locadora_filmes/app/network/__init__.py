"""Clientes de comunicacao HTTP da aplicacao desktop."""

from .api_client import (
    ApiClient,
    ApiClientError,
    ApiCommunicationError,
    ApiHttpError,
    ApiInvalidResponseError,
    ApiSerializationError,
    ApiTimeoutError,
)

__all__ = [
    'ApiClient',
    'ApiClientError',
    'ApiCommunicationError',
    'ApiHttpError',
    'ApiInvalidResponseError',
    'ApiSerializationError',
    'ApiTimeoutError',
]
