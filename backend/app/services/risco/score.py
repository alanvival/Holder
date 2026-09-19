"""Score de risco — função pura.

Regra de negócio: score = soma(peso × intensidade) dos sinais disparados,
limitado a [0, 1]. Para evitar alarme falso, um cliente com menos de 2
dimensões afetadas nunca passa de MONITORAR.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import FaixaRisco
from app.services.risco.sinais import Disparo


@dataclass(frozen=True)
class LimiaresFaixa:
    critico: float
    atencao: float
    monitorar: float


@dataclass(frozen=True)
class Evidencia:
    disparo: Disparo
    contribuicao: float


@dataclass(frozen=True)
class ResultadoScore:
    score: float
    faixa: FaixaRisco
    qtd_dimensoes_afetadas: int
    evidencias: list[Evidencia]


def classificar_faixa(score: float, qtd_dimensoes: int, limiares: LimiaresFaixa) -> FaixaRisco:
    if score >= limiares.critico:
        faixa = FaixaRisco.CRITICO
    elif score >= limiares.atencao:
        faixa = FaixaRisco.ATENCAO
    elif score >= limiares.monitorar:
        faixa = FaixaRisco.MONITORAR
    else:
        faixa = FaixaRisco.SAUDAVEL
    if qtd_dimensoes < 2 and faixa in (FaixaRisco.CRITICO, FaixaRisco.ATENCAO):
        faixa = FaixaRisco.MONITORAR
    return faixa


def calcular_score(disparos: list[Disparo], limiares: LimiaresFaixa) -> ResultadoScore:
    evidencias = sorted(
        (Evidencia(d, round(d.sinal.peso * d.intensidade, 4)) for d in disparos),
        key=lambda e: (-e.contribuicao, e.disparo.sinal.codigo),
    )
    score = round(min(1.0, sum(e.contribuicao for e in evidencias)), 4)
    qtd_dimensoes = len({e.disparo.sinal.dimensao for e in evidencias})
    return ResultadoScore(
        score=score,
        faixa=classificar_faixa(score, qtd_dimensoes, limiares),
        qtd_dimensoes_afetadas=qtd_dimensoes,
        evidencias=evidencias,
    )
