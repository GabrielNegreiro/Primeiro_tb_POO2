from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from .config import ConfigurationError
from .database import check_database_connection


app = FastAPI(
    title='Locadora API',
    description='Backend HTTP da Locadora de Filmes.',
    version='0.1.0',
)


@app.get('/health', tags=['health'])
def health():
    return {'status': 'ok', 'service': 'locadora-api'}


@app.get('/health/db', tags=['health'])
def health_database():
    try:
        connected = check_database_connection()
    except (ConfigurationError, ImportError, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Banco de dados indisponivel.',
        ) from None

    if not connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Banco de dados indisponivel.',
        )
    return {'status': 'ok', 'database': 'reachable'}

