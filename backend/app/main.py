from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .config import ConfigurationError
from .database import check_database_connection
from .routers.filmes import router as filmes_router
from .routers.locacoes import router as locacoes_router


app = FastAPI(
    title='Locadora API',
    description='Backend HTTP da Locadora de Filmes.',
    version='0.1.0',
)
app.include_router(filmes_router)
app.include_router(locacoes_router)


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(_request: Request, _error: SQLAlchemyError):
    """Converte falhas inesperadas de banco em resposta sem dados sensiveis."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={'detail': 'Falha ao acessar o banco de dados.'},
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

