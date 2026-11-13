from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={'connect_timeout': 3},
    )


def check_database_connection() -> bool:
    with get_engine().connect() as connection:
        return connection.execute(text('SELECT 1')).scalar_one() == 1

