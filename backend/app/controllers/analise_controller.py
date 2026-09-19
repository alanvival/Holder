from fastapi import APIRouter, Depends

from app.dependencies import get_analise_service, get_usuario_atual
from app.models import ExecucaoAnalise, Usuario
from app.schemas.analise import ExecucaoResponse
from app.services.analise_service import AnaliseService

router = APIRouter(prefix="/analise", tags=["analise"])


@router.post("/executar", response_model=ExecucaoResponse)
def executar(
    usuario: Usuario = Depends(get_usuario_atual),
    analise: AnaliseService = Depends(get_analise_service),
) -> ExecucaoAnalise:
    return analise.executar(usuario_id=usuario.id)
