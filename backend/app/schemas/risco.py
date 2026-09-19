from datetime import date

from pydantic import BaseModel

from app.core.enums import Dimensao, FaixaRisco, Responsavel


class AcaoResumo(BaseModel):
    codigo: str
    titulo: str
    responsavel: Responsavel
    prazo_dias: int


class AcaoDetalhe(AcaoResumo):
    descricao: str


class EvidenciaResponse(BaseModel):
    codigo_sinal: str
    dimensao: Dimensao
    texto: str
    valor_observado: float
    linha_base: float | None
    variacao_pct: float | None
    meses_persistencia: int
    contribuicao: float


class AvaliacaoRiscoResponse(BaseModel):
    mes_referencia: date
    score_risco: float
    faixa: FaixaRisco
    qtd_dimensoes_afetadas: int
    receita_em_risco: float
    posicao_fila: int | None
    evidencias: list[EvidenciaResponse]
    acao_recomendada: AcaoDetalhe | None
