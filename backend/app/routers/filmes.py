from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..repositories.filmes import FilmeRepository
from ..schemas.filmes import FilmeCreate, FilmeResponse, FilmeUpdate
from ..services.filmes import FilmeConflictError, FilmeNotFoundError, FilmeService


router = APIRouter(prefix='/filmes', tags=['filmes'])


def get_filme_service(session: Session = Depends(get_session)) -> FilmeService:
    """Monta o service com repository e sessao da requisicao atual."""
    return FilmeService(FilmeRepository(session), auto_commit=True)


def _not_found(error: FilmeNotFoundError) -> HTTPException:
    """Converte ausencia de dominio em uma resposta HTTP 404."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))


def _conflict(error: FilmeConflictError) -> HTTPException:
    """Converte conflito de dominio em uma resposta HTTP 409."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get('', response_model=list[FilmeResponse])
def listar_filmes(
    titulo: Optional[str] = Query(default=None, min_length=1),
    disponivel: Optional[bool] = Query(default=None),
    service: FilmeService = Depends(get_filme_service),
):
    """Lista filmes e aplica filtros opcionais cumulativos."""
    return service.listar(titulo=titulo, disponivel=disponivel)


@router.get('/{filme_id}', response_model=FilmeResponse)
def buscar_filme(
    filme_id: int = Path(gt=0),
    service: FilmeService = Depends(get_filme_service),
):
    """Consulta um filme pelo identificador."""
    try:
        return service.buscar_por_id(filme_id)
    except FilmeNotFoundError as error:
        raise _not_found(error) from None


@router.post('', response_model=FilmeResponse, status_code=status.HTTP_201_CREATED)
def criar_filme(
    dados: FilmeCreate,
    service: FilmeService = Depends(get_filme_service),
):
    """Cadastra um filme com identificador gerado pelo PostgreSQL."""
    return service.criar(dados)


@router.put('/{filme_id}', response_model=FilmeResponse)
def atualizar_filme(
    dados: FilmeUpdate,
    filme_id: int = Path(gt=0),
    service: FilmeService = Depends(get_filme_service),
):
    """Atualiza integralmente os campos editaveis de um filme."""
    try:
        return service.atualizar(filme_id, dados)
    except FilmeNotFoundError as error:
        raise _not_found(error) from None


@router.delete('/{filme_id}', status_code=status.HTTP_204_NO_CONTENT)
def excluir_filme(
    filme_id: int = Path(gt=0),
    service: FilmeService = Depends(get_filme_service),
):
    """Exclui um filme quando as regras e referencias permitem."""
    try:
        service.excluir(filme_id)
    except FilmeNotFoundError as error:
        raise _not_found(error) from None
    except FilmeConflictError as error:
        raise _conflict(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)

