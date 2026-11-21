from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..repositories.filmes import FilmeRepository
from ..repositories.locacoes import LocacaoRepository
from ..schemas.locacoes import (
    FiltroLocacao,
    LocacaoCreate,
    LocacaoDevolucaoRequest,
    LocacaoResponse,
    LocacaoUpdate,
)
from ..services.filmes import FilmeService
from ..services.locacoes import (
    LocacaoConflictError,
    LocacaoNotFoundError,
    LocacaoService,
    LocacaoValidationError,
)


router = APIRouter(prefix='/locacoes', tags=['locacoes'])


def get_locacao_service(session: Session = Depends(get_session)) -> LocacaoService:
    """Monta o service com repositories e a sessao da requisicao atual.

    O FilmeService usa auto_commit=False: somente o LocacaoService confirma,
    mantendo locacao e disponibilidade do filme na mesma transacao.
    """
    filme_service = FilmeService(FilmeRepository(session), auto_commit=False)
    return LocacaoService(
        LocacaoRepository(session),
        filme_service,
        auto_commit=True,
    )


def _http_error(error: Exception) -> HTTPException:
    """Converte excecoes de dominio em respostas HTTP 404, 409 ou 422."""
    if isinstance(error, LocacaoNotFoundError):
        codigo = status.HTTP_404_NOT_FOUND
    elif isinstance(error, LocacaoConflictError):
        codigo = status.HTTP_409_CONFLICT
    else:
        codigo = 422
    return HTTPException(status_code=codigo, detail=str(error))


_ERROS_DE_DOMINIO = (
    LocacaoNotFoundError,
    LocacaoConflictError,
    LocacaoValidationError,
)


@router.get('', response_model=list[LocacaoResponse])
def listar_locacoes(
    situacao: FiltroLocacao = Query(default=FiltroLocacao.TODAS),
    service: LocacaoService = Depends(get_locacao_service),
):
    """Lista locacoes: todas, ativas ou atrasadas."""
    return service.listar(situacao)


@router.get('/{locacao_id}', response_model=LocacaoResponse)
def buscar_locacao(
    locacao_id: int = Path(gt=0),
    service: LocacaoService = Depends(get_locacao_service),
):
    """Consulta uma locacao pelo identificador."""
    try:
        return service.buscar_por_id(locacao_id)
    except _ERROS_DE_DOMINIO as error:
        raise _http_error(error) from None


@router.post('', response_model=LocacaoResponse, status_code=status.HTTP_201_CREATED)
def criar_locacao(
    dados: LocacaoCreate,
    service: LocacaoService = Depends(get_locacao_service),
):
    """Registra uma locacao e torna o filme indisponivel."""
    try:
        return service.criar(dados)
    except _ERROS_DE_DOMINIO as error:
        raise _http_error(error) from None


@router.put('/{locacao_id}', response_model=LocacaoResponse)
def atualizar_locacao(
    dados: LocacaoUpdate,
    locacao_id: int = Path(gt=0),
    service: LocacaoService = Depends(get_locacao_service),
):
    """Edita filme, cliente ou prazo de uma locacao em aberto."""
    try:
        return service.atualizar(locacao_id, dados)
    except _ERROS_DE_DOMINIO as error:
        raise _http_error(error) from None


@router.post('/{locacao_id}/devolucao', response_model=LocacaoResponse)
def devolver_locacao(
    dados: Optional[LocacaoDevolucaoRequest] = None,
    locacao_id: int = Path(gt=0),
    service: LocacaoService = Depends(get_locacao_service),
):
    """Registra a devolucao; sem data no corpo, usa a data de hoje."""
    try:
        return service.devolver(locacao_id, dados)
    except _ERROS_DE_DOMINIO as error:
        raise _http_error(error) from None


@router.delete('/{locacao_id}', status_code=status.HTTP_204_NO_CONTENT)
def excluir_locacao(
    locacao_id: int = Path(gt=0),
    service: LocacaoService = Depends(get_locacao_service),
):
    """Exclui somente locacao ja devolvida."""
    try:
        service.excluir(locacao_id)
    except _ERROS_DE_DOMINIO as error:
        raise _http_error(error) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)