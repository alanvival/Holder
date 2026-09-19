from fastapi import APIRouter, Depends, Query

from app.dependencies import get_dashboard_service, get_usuario_atual
from app.schemas.dashboard import ItemFila, ResumoDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_usuario_atual)]
)


@router.get("/resumo", response_model=ResumoDashboard)
def resumo(service: DashboardService = Depends(get_dashboard_service)) -> ResumoDashboard:
    return service.resumo()


@router.get("/fila", response_model=list[ItemFila])
def fila(
    limite: int = Query(10, ge=1, le=100, description="Máximo de itens da fila"),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[ItemFila]:
    return service.fila(limite)
