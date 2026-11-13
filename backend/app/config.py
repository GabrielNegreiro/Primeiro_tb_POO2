import os
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import URL


class ConfigurationError(RuntimeError):
    pass


def _required_environment(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value:
        raise ConfigurationError(f'Variavel de ambiente obrigatoria ausente: {name}')
    return value


@dataclass(frozen=True)
class Settings:
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_host: str
    database_port: int

    @classmethod
    def from_environment(cls):
        try:
            database_port = int(os.getenv('DATABASE_PORT', '5432'))
        except ValueError as error:
            raise ConfigurationError('DATABASE_PORT deve ser um numero inteiro.') from error

        return cls(
            postgres_db=_required_environment('POSTGRES_DB'),
            postgres_user=_required_environment('POSTGRES_USER'),
            postgres_password=_required_environment('POSTGRES_PASSWORD'),
            database_host=os.getenv('DATABASE_HOST', 'db').strip() or 'db',
            database_port=database_port,
        )

    def database_url(self) -> URL:
        return URL.create(
            drivername='postgresql+psycopg',
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.database_host,
            port=self.database_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()

