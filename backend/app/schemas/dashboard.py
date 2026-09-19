from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import Dimensao, FaixaRisco, Plano, Porte
from app.schemas.risco import AcaoResumo


class ResumoDashboard(BaseModel):
    mes_referencia: date | None
    executado_em: datetime | None
    clientes_ativos: int
    receita_ativa: float
    receita_em_risco: float
    qtd_na_fila: int
    por_faixa: dict[FaixaRisco, int]
    por_dimensao: dict[Dimensao, int]


class ItemFila(BaseModel):
    posicao: int
    cliente_id: str
    segmento: str
    plano: Plano
    porte: Porte
    valor_mensal: float
    score_risco: float
    faixa: FaixaRisco
    receita_em_risco: float
    qtd_dimensoes_afetadas: int
    principais_motivos: list[str]
    acao_recomendada: AcaoResumo | None
    ultimo_contato: None = None
