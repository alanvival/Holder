"""
As cinco agregações nomeadas que toda métrica do catálogo usa: média, média
ponderada, razão de somas, proporção de linhas e soma.

São as mesmas cinco do resolvedor em JavaScript
(`interface-web/src/engine/metricas.js`, função `agregar`). É isso que
torna a duplicação do resolvedor sustentável: a fórmula de cada métrica não
está espalhada pelo código, está na combinação de uma definição declarativa
com uma destas agregações. Ver
`docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md`.
"""
from __future__ import annotations

import datetime as dt


def media(serie):
    serie = serie.dropna()
    if len(serie) == 0:
        return None
    return float(serie.mean())


def media_ponderada(df, campo, campo_peso):
    df = df[df[campo_peso] > 0]
    df = df.dropna(subset=[campo])
    if len(df) == 0 or df[campo_peso].sum() == 0:
        return None
    return float((df[campo] * df[campo_peso]).sum() / df[campo_peso].sum())


def razao_soma(df, numerador, denominador):
    den = df[denominador].sum()
    if den == 0:
        return None
    return float(df[numerador].sum() / den)


def soma(serie):
    return float(serie.dropna().sum())


def media_de_lista(valores):
    """Média de uma lista Python já extraída de um DataFrame, descartando
    None e NaN (`v == v` é falso só para NaN). Usada pelo índice de alerta,
    que compara o mês atual com a média dos meses anteriores."""
    limpos = [v for v in valores if v is not None and v == v]
    if not limpos:
        return None
    return sum(limpos) / len(limpos)


def antiguidade_dias(df):
    """Dias desde inicio_contrato até hoje — usado pela métrica
    'antiguidade_contrato' (não é campo numérico direto, precisa parsear a
    data primeiro). Datas inválidas/vazias são ignoradas, não zeradas."""
    if len(df) == 0:
        return None
    hoje = dt.date.today()
    dias = []
    for valor in df["inicio_contrato"]:
        try:
            inicio = dt.date.fromisoformat(str(valor)[:10])
        except (ValueError, TypeError):
            continue
        dias.append((hoje - inicio).days)
    if not dias:
        return None
    return sum(dias) / len(dias)
