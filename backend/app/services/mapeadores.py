"""Conversão de models para os schemas de resposta (a "View")."""

from app.models import AcaoRecomendada, AvaliacaoRisco, EvidenciaRisco
from app.schemas.dashboard import ItemFila
from app.schemas.risco import AcaoDetalhe, AcaoResumo, AvaliacaoRiscoResponse, EvidenciaResponse

QTD_MOTIVOS = 3


def _opcional(valor: object) -> float | None:
    return None if valor is None else float(valor)  # type: ignore[arg-type]


def acao_resumo(acao: AcaoRecomendada | None) -> AcaoResumo | None:
    if acao is None:
        return None
    return AcaoResumo(
        codigo=acao.codigo,
        titulo=acao.titulo,
        responsavel=acao.responsavel_sugerido,
        prazo_dias=acao.prazo_dias,
    )


def acao_detalhe(acao: AcaoRecomendada | None) -> AcaoDetalhe | None:
    if acao is None:
        return None
    return AcaoDetalhe(
        codigo=acao.codigo,
        titulo=acao.titulo,
        responsavel=acao.responsavel_sugerido,
        prazo_dias=acao.prazo_dias,
        descricao=acao.descricao,
    )


def evidencia_response(evidencia: EvidenciaRisco) -> EvidenciaResponse:
    return EvidenciaResponse(
        codigo_sinal=evidencia.sinal.codigo,
        dimensao=evidencia.dimensao,
        texto=evidencia.texto,
        valor_observado=float(evidencia.valor_observado),
        linha_base=_opcional(evidencia.linha_base),
        variacao_pct=_opcional(evidencia.variacao_pct),
        meses_persistencia=evidencia.meses_persistencia,
        contribuicao=float(evidencia.contribuicao),
    )


def avaliacao_response(avaliacao: AvaliacaoRisco) -> AvaliacaoRiscoResponse:
    return AvaliacaoRiscoResponse(
        mes_referencia=avaliacao.mes_referencia,
        score_risco=float(avaliacao.score_risco),
        faixa=avaliacao.faixa,
        qtd_dimensoes_afetadas=avaliacao.qtd_dimensoes_afetadas,
        receita_em_risco=float(avaliacao.receita_em_risco),
        posicao_fila=avaliacao.posicao_fila,
        evidencias=[evidencia_response(e) for e in avaliacao.evidencias],
        acao_recomendada=acao_detalhe(avaliacao.acao_recomendada),
    )


def item_fila(avaliacao: AvaliacaoRisco) -> ItemFila:
    cliente = avaliacao.cliente
    return ItemFila(
        posicao=avaliacao.posicao_fila or 0,
        cliente_id=cliente.cliente_id,
        segmento=cliente.segmento,
        plano=cliente.plano,
        porte=cliente.porte,
        valor_mensal=float(cliente.valor_mensal),
        score_risco=float(avaliacao.score_risco),
        faixa=avaliacao.faixa,
        receita_em_risco=float(avaliacao.receita_em_risco),
        qtd_dimensoes_afetadas=avaliacao.qtd_dimensoes_afetadas,
        principais_motivos=[e.texto for e in avaliacao.evidencias[:QTD_MOTIVOS]],
        acao_recomendada=acao_resumo(avaliacao.acao_recomendada),
    )
