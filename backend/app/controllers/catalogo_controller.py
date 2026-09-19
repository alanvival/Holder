from fastapi import APIRouter, Depends

from app.dependencies import get_catalogo_service, get_usuario_atual
from app.models import AcaoRecomendada, ConfiguracaoSinal
from app.schemas.catalogo import AcaoResponse, SinalResponse
from app.services.catalogo_service import CatalogoService

router = APIRouter(tags=["catalogo"], dependencies=[Depends(get_usuario_atual)])


@router.get("/sinais", response_model=list[SinalResponse])
def sinais(service: CatalogoService = Depends(get_catalogo_service)) -> list[ConfiguracaoSinal]:
    return service.listar_sinais()


@router.get("/acoes-recomendadas", response_model=list[AcaoResponse])
def acoes(service: CatalogoService = Depends(get_catalogo_service)) -> list[AcaoRecomendada]:
    return service.listar_acoes()
