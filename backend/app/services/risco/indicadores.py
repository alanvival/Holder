"""Indicadores mensais por cliente — função pura, sem acesso ao banco.

Regra de negócio: cada indicador do mês M usa somente dados até M
(sem vazamento do futuro). Para cada variável calculamos o nível recente
(média/soma dos últimos 3 meses), a linha de base (média dos 6 meses
anteriores a essa janela), a variação relativa e há quantos meses seguidos
o valor está pior que a base.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from app.core.enums import SentidoPiora

# Denominador mínimo da variação relativa: evita percentuais explosivos
# quando a linha de base é ~0 (ex.: nenhum chamado reaberto no passado).
DENOMINADOR_MINIMO = 0.5

SENTIDO_PIORA: dict[str, SentidoPiora] = {
    "chamados_abertos": SentidoPiora.AUMENTO,
    "chamados_criticos": SentidoPiora.AUMENTO,
    "chamados_reabertos": SentidoPiora.AUMENTO,
    "taxa_reabertura": SentidoPiora.AUMENTO,
    "pct_sla_cumprido": SentidoPiora.QUEDA,
    "tempo_resolucao_vs_sla": SentidoPiora.AUMENTO,
    "reclamacoes_formais": SentidoPiora.AUMENTO,
    "uso_plataforma_pct": SentidoPiora.QUEDA,
    "dias_atraso_pagamento": SentidoPiora.AUMENTO,
    "pct_reunioes_realizadas": SentidoPiora.QUEDA,
    "nps_nota": SentidoPiora.QUEDA,
    "nps_variacao": SentidoPiora.QUEDA,
    "nps_sem_resposta_consecutivas": SentidoPiora.AUMENTO,
}

COLUNAS_SAIDA = [
    "cliente_id",
    "variavel",
    "valor_mes",
    "media_3m",
    "soma_3m",
    "linha_base_6m",
    "variacao_pct",
    "meses_consecutivos_piora",
]


def somar_meses(mes: date, n: int) -> date:
    """Soma n meses (pode ser negativo) a uma data de dia 1."""
    ano, indice = divmod(mes.year * 12 + mes.month - 1 + n, 12)
    return date(ano, indice + 1, 1)


def _meses_entre(inicio: date, fim: date) -> list[date]:
    meses = []
    atual = inicio
    while atual <= fim:
        meses.append(atual)
        atual = somar_meses(atual, 1)
    return meses


def _numerico(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce").astype(float)


def _derivar_atendimento(atendimentos: pd.DataFrame, sla_por_cliente: pd.Series) -> pd.DataFrame:
    at = atendimentos.copy()
    abertos = _numerico(at["chamados_abertos"])
    tem_chamado = abertos > 0
    sla = _numerico(at["cliente_id"].map(sla_por_cliente))
    at["taxa_reabertura"] = (_numerico(at["chamados_reabertos"]) / abertos).where(tem_chamado)
    # Sem chamado no mês não há tempo de resolução a medir: fica nulo.
    at["tempo_resolucao_vs_sla"] = (_numerico(at["tempo_medio_resolucao_h"]) / sla).where(
        tem_chamado
    )
    previstas = _numerico(at["reunioes_previstas"])
    at["pct_reunioes_realizadas"] = (_numerico(at["reunioes_realizadas"]) / previstas).where(
        previstas > 0
    )
    return at


def _estado_nps(pesquisas_cliente: pd.DataFrame, meses: list[date]) -> pd.DataFrame:
    """Estado do NPS em cada mês, olhando só as pesquisas até aquele mês."""
    pesquisas = pesquisas_cliente.sort_values("mes_ref")
    linhas = []
    for mes in meses:
        ate_mes = pesquisas[pesquisas["mes_ref"] <= mes]
        respondeu = ate_mes["respondeu"].astype(bool)
        notas = _numerico(ate_mes["nota_nps"][respondeu]).dropna().tolist()
        silencio = 0
        if notas:  # o silêncio só é sinal se o cliente já respondeu antes
            for resposta in reversed(respondeu.tolist()):
                if resposta:
                    break
                silencio += 1
        linhas.append(
            {
                "nps_nota": notas[-1] if notas else np.nan,
                "nps_variacao": notas[-1] - notas[-2] if len(notas) >= 2 else np.nan,
                "nps_sem_resposta_consecutivas": float(silencio),
            }
        )
    return pd.DataFrame(linhas, index=meses)


def _resumir_serie(serie: pd.Series, sentido: SentidoPiora) -> dict[str, float | int]:
    serie = serie.astype(float)
    media_3m = serie.rolling(3, min_periods=1).mean()
    soma_3m = serie.rolling(3, min_periods=1).sum()
    linha_base = serie.shift(3).rolling(6, min_periods=1).mean()
    pior = serie > linha_base if sentido == SentidoPiora.AUMENTO else serie < linha_base
    pior = pior & serie.notna() & linha_base.notna()
    consecutivos = 0
    for mes_pior in reversed(pior.tolist()):
        if not mes_pior:
            break
        consecutivos += 1
    media, base = media_3m.iloc[-1], linha_base.iloc[-1]
    variacao = (
        (media - base) / max(abs(base), DENOMINADOR_MINIMO)
        if pd.notna(media) and pd.notna(base)
        else np.nan
    )
    return {
        "valor_mes": serie.iloc[-1],
        "media_3m": media,
        "soma_3m": soma_3m.iloc[-1],
        "linha_base_6m": base,
        "variacao_pct": variacao,
        "meses_consecutivos_piora": consecutivos,
    }


def calcular_indicadores(
    atendimentos: pd.DataFrame,
    pesquisas: pd.DataFrame,
    clientes: pd.DataFrame,
    mes_referencia: date,
) -> pd.DataFrame:
    """Indicadores de cada cliente × variável no mês de referência.

    Clientes sem nenhum atendimento até o mês de referência ficam de fora.
    """
    at = atendimentos[atendimentos["mes_ref"] <= mes_referencia]
    if at.empty:
        return pd.DataFrame(columns=COLUNAS_SAIDA)
    pq = pesquisas[pesquisas["mes_ref"] <= mes_referencia]
    sla = clientes.set_index("cliente_id")["sla_contratado_h"]
    at = _derivar_atendimento(at, sla)

    linhas = []
    for cliente_id, grupo in at.groupby("cliente_id", sort=True):
        meses = _meses_entre(min(grupo["mes_ref"]), mes_referencia)
        painel = grupo.set_index("mes_ref").reindex(meses)
        painel = painel.join(_estado_nps(pq[pq["cliente_id"] == cliente_id], meses))
        for variavel, sentido in SENTIDO_PIORA.items():
            linhas.append(
                {
                    "cliente_id": cliente_id,
                    "variavel": variavel,
                    **_resumir_serie(painel[variavel], sentido),
                }
            )
    return pd.DataFrame(linhas, columns=COLUNAS_SAIDA)
