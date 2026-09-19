"""Avaliação de sinais de risco sobre os indicadores — funções puras.

Regras de disparo:
- TENDENCIA: variação relativa (invertida se o sentido de piora é QUEDA) ≥ limiar
  e piora persistente por `persistencia_min_meses` meses seguidos.
- NIVEL: `metrica` (media_3m ou soma_3m) acima (AUMENTO) ou abaixo (QUEDA) do limiar;
  a janela de 3 meses já expressa persistência.
- EVENTO: valor do mês (invertido se QUEDA) ≥ limiar.
Métrica nula nunca dispara. A intensidade vai de 0,5 (no limiar) a 1,0 (2× o limiar).
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.enums import Dimensao, SentidoPiora, TipoRegra

Indicador = Mapping[str, Any]


@dataclass(frozen=True)
class DefinicaoSinal:
    id: int | None
    codigo: str
    dimensao: Dimensao
    variavel: str
    tipo_regra: TipoRegra
    sentido_piora: SentidoPiora
    limiar: float
    persistencia_min_meses: int
    peso: float
    template_evidencia: str
    metrica: str = "media_3m"


@dataclass(frozen=True)
class Disparo:
    sinal: DefinicaoSinal
    valor_observado: float
    linha_base: float | None
    variacao_pct: float | None
    meses_persistencia: int
    intensidade: float
    texto: str


def _nulo(valor: Any) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _opcional(valor: Any) -> float | None:
    return None if _nulo(valor) else float(valor)


def preencher_template(template: str, indicador: Indicador) -> str:
    """Preenche o texto da evidência; campos nulos viram 0."""
    ctx = {
        chave: 0.0 if _nulo(indicador.get(chave)) else float(indicador[chave])
        for chave in ("valor_mes", "media_3m", "soma_3m", "linha_base_6m", "variacao_pct")
    }
    ctx["linha_base"] = ctx["linha_base_6m"]
    ctx["queda_pct"] = -ctx["variacao_pct"]
    ctx["queda_abs"] = -ctx["valor_mes"]
    return template.format(**ctx)


def avaliar_sinal(sinal: DefinicaoSinal, indicador: Indicador) -> Disparo | None:
    """Retorna o disparo do sinal para um indicador (cliente × variável) ou None."""
    persistencia = int(indicador.get("meses_consecutivos_piora") or 0)
    limiar = sinal.limiar
    if sinal.tipo_regra == TipoRegra.NIVEL:
        bruto = indicador.get(sinal.metrica)
        if _nulo(bruto):
            return None
        bruto = float(bruto)
        if sinal.sentido_piora == SentidoPiora.AUMENTO:
            dispara, excesso = bruto >= limiar, (bruto - limiar) / abs(limiar)
        else:
            dispara, excesso = bruto <= limiar, (limiar - bruto) / abs(limiar)
    else:
        campo = "variacao_pct" if sinal.tipo_regra == TipoRegra.TENDENCIA else "valor_mes"
        bruto = indicador.get(campo)
        if _nulo(bruto):
            return None
        bruto = float(bruto)
        orientado = -bruto if sinal.sentido_piora == SentidoPiora.QUEDA else bruto
        dispara, excesso = orientado >= limiar, (orientado - limiar) / abs(limiar)
        if sinal.tipo_regra == TipoRegra.TENDENCIA and persistencia < sinal.persistencia_min_meses:
            dispara = False
    if not dispara:
        return None
    return Disparo(
        sinal=sinal,
        valor_observado=bruto,
        linha_base=_opcional(indicador.get("linha_base_6m")),
        variacao_pct=_opcional(indicador.get("variacao_pct")),
        meses_persistencia=persistencia,
        intensidade=0.5 + 0.5 * min(1.0, max(0.0, excesso)),
        texto=preencher_template(sinal.template_evidencia, indicador),
    )


def avaliar_sinais(
    sinais: list[DefinicaoSinal], indicadores_cliente: Mapping[str, Indicador]
) -> list[Disparo]:
    """Avalia todos os sinais de um cliente. `indicadores_cliente` é variavel -> indicador."""
    disparos = []
    for sinal in sinais:
        indicador = indicadores_cliente.get(sinal.variavel)
        if indicador is None:
            continue
        disparo = avaliar_sinal(sinal, indicador)
        if disparo is not None:
            disparos.append(disparo)
    return disparos
