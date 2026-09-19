from datetime import date

from pydantic import BaseModel, ConfigDict

from app.core.enums import ClassificacaoNPS, FaixaRisco, Plano, Porte, SituacaoCliente
from app.schemas.risco import AvaliacaoRiscoResponse


class ClienteResumo(BaseModel):
    cliente_id: str
    segmento: str
    porte: Porte
    plano: Plano
    valor_mensal: float
    sla_contratado_h: int
    inicio_contrato: date
    situacao: SituacaoCliente | None
    mes_cancelamento: date | None
    score_risco: float | None = None
    faixa: FaixaRisco | None = None
    receita_em_risco: float | None = None
    posicao_fila: int | None = None


class ClienteDetalhe(ClienteResumo):
    avaliacao: AvaliacaoRiscoResponse | None = None


class AtendimentoMes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes_ref: date
    chamados_abertos: int
    chamados_criticos: int
    chamados_reabertos: int
    chamados_dentro_sla: int
    pct_sla_cumprido: float | None
    tempo_medio_resolucao_h: float
    reclamacoes_formais: int
    uso_plataforma_pct: float
    dias_atraso_pagamento: int
    reunioes_previstas: int
    reunioes_realizadas: int


class NpsMes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mes_ref: date
    respondeu: bool
    nota_nps: int | None
    classificacao_nps: ClassificacaoNPS


class HistoricoCliente(BaseModel):
    cliente_id: str
    atendimento: list[AtendimentoMes]
    nps: list[NpsMes]
