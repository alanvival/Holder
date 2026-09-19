"""Monta services com seus repositories (usado pela API e pelos scripts)."""

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.acao_repository import AcaoRepository
from app.repositories.atendimento_repository import AtendimentoRepository
from app.repositories.cliente_repository import ClienteRepository
from app.repositories.execucao_repository import ExecucaoRepository
from app.repositories.nps_repository import NpsRepository
from app.repositories.origem_repository import OrigemRepository
from app.repositories.sinal_repository import SinalRepository
from app.services.analise_service import AnaliseService
from app.services.catalogo_service import CatalogoService
from app.services.importacao_service import ImportacaoService


def criar_catalogo_service(session: Session, settings: Settings) -> CatalogoService:
    return CatalogoService(
        SinalRepository(session), AcaoRepository(session), settings.persistencia_min_meses
    )


def criar_importacao_service(session: Session, settings: Settings) -> ImportacaoService:
    return ImportacaoService(OrigemRepository(session), criar_catalogo_service(session, settings))


def criar_analise_service(session: Session, settings: Settings) -> AnaliseService:
    return AnaliseService(
        ClienteRepository(session),
        AtendimentoRepository(session),
        NpsRepository(session),
        SinalRepository(session),
        AcaoRepository(session),
        ExecucaoRepository(session),
        settings,
    )
