from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente
from app.dependencies import get_cliente_service, get_usuario_atual
from app.schemas.cliente import ClienteDetalhe, ClienteResumo, HistoricoCliente
from app.schemas.comum import Pagina
from app.services.cliente_service import ClienteService

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(get_usuario_atual)])

Ordenacao = Literal["cliente_id", "valor_mensal", "score", "receita_em_risco"]


@router.get("", response_model=Pagina[ClienteResumo])
def listar(
    situacao: SituacaoCliente | None = None,
    faixa: FaixaRisco | None = None,
    plano: Plano | None = None,
    porte: Porte | None = None,
    segmento: str | None = Query(None, examples=["Saude"]),
    busca: str | None = Query(None, description="Trecho do código ou do segmento"),
    ordenar: Ordenacao = "cliente_id",
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=100),
    service: ClienteService = Depends(get_cliente_service),
) -> Pagina[ClienteResumo]:
    return service.listar(
        situacao=situacao,
        faixa=faixa,
        plano=plano,
        porte=porte,
        segmento=segmento,
        busca=busca,
        ordenar=ordenar,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/{cliente_id}", response_model=ClienteDetalhe)
def detalhe(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
) -> ClienteDetalhe:
    return service.detalhe(cliente_id)


@router.get("/{cliente_id}/historico", response_model=HistoricoCliente)
def historico(
    cliente_id: str, service: ClienteService = Depends(get_cliente_service)
) -> HistoricoCliente:
    return service.historico(cliente_id)
