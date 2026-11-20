from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Cria o engine compartilhado com verificacao de conexao do pool."""
    return create_engine(
        get_settings().database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={'connect_timeout': 3},
    )


@lru_cache
def get_session_factory():
    """Retorna a fabrica de sessoes vinculada ao engine da aplicacao."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Generator[Session, None, None]:
    """Fornece uma sessao transacional por requisicao HTTP."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """Executa uma consulta minima para confirmar o acesso ao PostgreSQL."""
    with get_engine().connect() as connection:
        return connection.execute(text('SELECT 1')).scalar_one() == 1

