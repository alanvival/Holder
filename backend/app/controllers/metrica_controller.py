from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_metrica_service, get_usuario_atual
from app.schemas.metrica import PontoMensal, VariavelMetrica
from app.services.metrica_service import MetricaService

router = APIRouter(prefix="/metricas", tags=["metricas"], dependencies=[Depends(get_usuario_atual)])


@router.get("/variaveis", response_model=list[VariavelMetrica])
def variaveis(service: MetricaService = Depends(get_metrica_service)) -> list[VariavelMetrica]:
    return service.variaveis()


@router.get("/mensal", response_model=list[PontoMensal])
def mensal(
    variavel: str = Query(..., examples=["pct_sla_cumprido"]),
    agregacao: Literal["media", "soma"] = "media",
    service: MetricaService = Depends(get_metrica_service),
) -> list[PontoMensal]:
    return service.mensal(variavel, agregacao)
