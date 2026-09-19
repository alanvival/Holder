"""
Port em Python do motor de métricas (assistente-consultas/src/engine/
metricas.js) — mesma arquitetura (definição declarativa + resolvedor
genérico), mesmas fórmulas e exclusões, validadas contra os mesmos números
de referência do prompt de métricas. É a função que a tool `consultar_metrica`
chama de verdade: a Claude nunca calcula nada, só escolhe a métrica e os
filtros — quem soma e divide é este módulo.
"""
from __future__ import annotations

import math

from . import dados

PLANO_LABELS = {"Essencial": "Essencial", "Avancado": "Avançado", "Enterprise": "Enterprise"}
PORTE_LABELS = {"Pequeno": "Pequeno", "Medio": "Médio", "Grande": "Grande"}


def _media(serie):
    serie = serie.dropna()
    if len(serie) == 0:
        return None
    return float(serie.mean())


def _media_ponderada(df, campo, campo_peso):
    df = df[df[campo_peso] > 0]
    df = df.dropna(subset=[campo])
    if len(df) == 0 or df[campo_peso].sum() == 0:
        return None
    return float((df[campo] * df[campo_peso]).sum() / df[campo_peso].sum())


def _razao_soma(df, numerador, denominador):
    den = df[denominador].sum()
    if den == 0:
        return None
    return float(df[numerador].sum() / den)


def _soma(serie):
    return float(serie.dropna().sum())


def _calcular_nps(df):
    respondidas = df[df["respondeu"] == 1]
    if len(respondidas) == 0:
        return None
    promotores = (respondidas["classificacao_nps"] == "Promotor").sum()
    detratores = (respondidas["classificacao_nps"] == "Detrator").sum()
    return {
        "score": float((promotores - detratores) / len(respondidas) * 100),
        "nota_media": float(respondidas["nota_nps"].mean()),
        "respondidas": int(len(respondidas)),
        "convites": int(len(df)),
    }


# Cada entrada espelha uma métrica de METRICAS em metricas.js — mesma
# fórmula, mesmas exclusões, mesmo campo de origem.
METRICAS = {
    "ticket_medio": {
        "rotulo": "Ticket médio",
        "aba": "clientes",
        "formato": "moeda",
        "calcular": lambda df: _media(df["valor_mensal"]),
    },
    "tempo_medio_resolucao": {
        "rotulo": "Tempo médio de resolução",
        "aba": "atendimento_mensal",
        "formato": "horas",
        # Exclui linhas sem chamado (residual de tempo sem chamado real).
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: _media_ponderada(df, "tempo_medio_resolucao_h", "chamados_abertos"),
        "leitura_alternativa": {
            "rotulo": "média simples (sem ponderar pelo volume de chamados)",
            "calcular": lambda df: _media(df["tempo_medio_resolucao_h"]),
        },
    },
    "media_reclamacoes": {
        "rotulo": "Média de reclamações",
        "aba": "atendimento_mensal",
        "formato": "numero",
        "calcular": lambda df: _media(df["reclamacoes_formais"]),
    },
    "atraso_pagamento": {
        "rotulo": "Atraso médio de pagamento",
        "aba": "atendimento_mensal",
        "formato": "dias",
        "calcular": lambda df: _media(df["dias_atraso_pagamento"]),
    },
    "sla_cumprido": {
        "rotulo": "SLA cumprido",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: _razao_soma(df, "chamados_dentro_sla", "chamados_abertos"),
        "escala100": True,
        "leitura_alternativa": {
            "rotulo": "média simples do percentual mensal já calculado",
            "calcular": lambda df: _media(df["pct_sla_cumprido"]),
        },
    },
    "churn": {
        "rotulo": "Taxa de cancelamento (churn)",
        "aba": "situacao_clientes",
        "formato": "percentual",
        "escala100": True,
        "calcular": lambda df: float((df["situacao"] == "Cancelado").mean()) if len(df) else None,
    },
    "uso_plataforma": {
        "rotulo": "Uso médio da plataforma",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "calcular": lambda df: _media(df["uso_plataforma_pct"]),
    },
    "reunioes_realizadas": {
        "rotulo": "Reuniões realizadas",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "escala100": True,
        "calcular": lambda df: _razao_soma(df, "reunioes_realizadas", "reunioes_previstas"),
    },
    "chamados_criticos": {
        "rotulo": "Chamados críticos",
        "aba": "atendimento_mensal",
        "formato": "inteiro",
        "calcular": lambda df: _soma(df["chamados_criticos"]),
    },
    "taxa_reabertura": {
        "rotulo": "Taxa de reabertura",
        "aba": "atendimento_mensal",
        "formato": "percentual",
        "escala100": True,
        "filtro_linha": lambda df: df[df["chamados_abertos"] > 0],
        "calcular": lambda df: _razao_soma(df, "chamados_reabertos", "chamados_abertos"),
    },
    "nps": {
        "rotulo": "NPS",
        "aba": "pesquisas_nps",
        "formato": "nps",
        "calcular": _calcular_nps,
    },
}

_ABAS = {
    "clientes": dados.clientes,
    "atendimento_mensal": dados.atendimento_mensal,
    "pesquisas_nps": dados.pesquisas_nps,
    "situacao_clientes": dados.situacao_clientes,
}


def _aba_tem_periodo(aba):
    return aba in ("atendimento_mensal", "pesquisas_nps")


def _filtrar(aba, filtros):
    df = _ABAS[aba]

    cliente_id = filtros.get("cliente_id")
    plano = filtros.get("plano")
    porte = filtros.get("porte")
    segmento = filtros.get("segmento")
    situacao = filtros.get("situacao")
    inicio = filtros.get("periodo_inicio")
    fim = filtros.get("periodo_fim")

    if cliente_id:
        df = df[df["cliente_id"] == cliente_id]
    if plano:
        df = df[df["cliente_id"].map(dados.plano_do_cliente) == plano]
    if porte:
        df = df[df["cliente_id"].map(dados.porte_do_cliente) == porte]
    if segmento:
        df = df[df["cliente_id"].map(dados.segmento_do_cliente) == segmento]
    if situacao:
        df = df[df["cliente_id"].map(dados.situacao_do_cliente) == situacao]
    if _aba_tem_periodo(aba):
        if inicio:
            df = df[df["mes_ref"] >= inicio]
        if fim:
            df = df[df["mes_ref"] <= fim]

    return df


def _descrever_universo(aba, filtros, df):
    n_clientes = df["cliente_id"].nunique() if "cliente_id" in df.columns else 0
    partes = [f"{n_clientes} cliente(s)"]
    if filtros.get("plano"):
        partes.append(f"plano {PLANO_LABELS.get(filtros['plano'], filtros['plano'])}")
    if filtros.get("porte"):
        partes.append(f"porte {PORTE_LABELS.get(filtros['porte'], filtros['porte'])}")
    if filtros.get("segmento"):
        partes.append(f"segmento {filtros['segmento']}")
    if filtros.get("situacao"):
        partes.append("ativos" if filtros["situacao"] == "Ativo" else "cancelados")
    if filtros.get("cliente_id"):
        partes.append(f"cliente {filtros['cliente_id']}")

    descricao = f"Considerando {', '.join(partes)}"
    if _aba_tem_periodo(aba):
        inicio = filtros.get("periodo_inicio") or dados.PRIMEIRO_MES_DADOS
        fim = filtros.get("periodo_fim") or dados.ULTIMO_MES_DADOS
        descricao += f", de {inicio} a {fim}"
    return descricao + "."


def calcular_metrica(metrica_id: str, filtros: dict | None = None) -> dict:
    """
    Único ponto que sabe calcular qualquer métrica — é isso que a tool
    `consultar_metrica` chama. Retorna sempre um dict JSON-serializável com
    o valor bruto (nunca formatado como string livre — quem decide o texto
    final é a Claude, em cima deste número real) e o universo considerado.
    """
    filtros = filtros or {}
    definicao = METRICAS.get(metrica_id)
    if not definicao:
        return {"erro": f"Métrica desconhecida: {metrica_id}"}

    df = _filtrar(definicao["aba"], filtros)
    if len(df) == 0:
        return {"erro": "Sem dados para essa combinação de filtros.", "universo": _descrever_universo(definicao["aba"], filtros, df)}

    df_calculo = definicao["filtro_linha"](df) if "filtro_linha" in definicao else df

    valor = definicao["calcular"](df_calculo)
    if valor is None:
        return {"erro": "Sem amostra suficiente para essa métrica com esses filtros."}

    resultado = {
        "metrica": metrica_id,
        "rotulo": definicao["rotulo"],
        "formato": definicao["formato"],
        "universo": _descrever_universo(definicao["aba"], filtros, df),
    }

    if metrica_id == "nps":
        resultado.update(valor)  # já é um dict {score, nota_media, respondidas, convites}
    else:
        escalado = valor * 100 if definicao.get("escala100") else valor
        resultado["valor"] = round(escalado, 4) if isinstance(escalado, float) else escalado

        if "leitura_alternativa" in definicao:
            alt = definicao["leitura_alternativa"]["calcular"](df_calculo)
            if alt is not None:
                alt_escalado = alt * 100 if definicao.get("escala100") else alt
                resultado["leitura_alternativa"] = {
                    "rotulo": definicao["leitura_alternativa"]["rotulo"],
                    "valor": round(alt_escalado, 4),
                }

    return resultado
