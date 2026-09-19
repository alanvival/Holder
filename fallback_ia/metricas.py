"""
Port em Python do motor de métricas (assistente-consultas/src/engine/
metricas.js) — mesma arquitetura (definição declarativa + resolvedor
genérico), mesmas fórmulas e exclusões, validadas contra os mesmos números
de referência do prompt de métricas. É a função que a tool `consultar_metrica`
chama de verdade: a Claude nunca calcula nada, só escolhe a métrica e os
filtros — quem soma e divide é este módulo.
"""
from __future__ import annotations

import datetime as dt
import math

from . import dados

PLANO_LABELS = {"Essencial": "Essencial", "Avancado": "Avançado", "Enterprise": "Enterprise"}
PORTE_LABELS = {"Pequeno": "Pequeno", "Medio": "Médio", "Grande": "Grande"}


def _media(serie):
    serie = serie.dropna()
    if len(serie) == 0:
        return None
    return float(serie.mean())


def _antiguidade_dias(df):
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
    "antiguidade_contrato": {
        "rotulo": "Antiguidade do contrato",
        "aba": "clientes",
        "formato": "dias",
        # Ranking por "maior" = contrato mais VELHO (mais dias desde o
        # início) = cliente mais antigo; "menor" = cliente mais novo.
        "calcular": _antiguidade_dias,
    },
    "sla_contratado": {
        # Diferente de "sla_cumprido" (% de chamados dentro do prazo, mês a
        # mês) — este é o PRAZO em horas que consta no contrato, fixo por
        # cliente (6h Enterprise / 12h Avançado / 24h Essencial nesta base).
        "rotulo": "SLA contratado",
        "aba": "clientes",
        "formato": "horas",
        "calcular": lambda df: _media(df["sla_contratado_h"]),
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


# Métricas comparáveis entre os dois grupos (Ativo/Cancelado) — exclui NPS
# (estrutura diferente, tratado à parte) e churn (é a própria coisa que
# estamos comparando, não faria sentido comparar "churn" contra si mesmo).
#
# IMPORTANTE: todas aqui precisam ser MÉDIA por cliente-mês, nunca soma —
# os grupos têm números de linhas diferentes (clientes cancelados têm menos
# meses de histórico total, já que o histórico deles para no cancelamento),
# então comparar somas brutas entre os dois grupos é enviesado por tamanho
# de amostra, não pela taxa real. "chamados_criticos" no catálogo normal
# usa soma (faz sentido pra "quantos no total"), então aqui ele entra à
# parte, calculado como média.
_METRICAS_PARA_ANALISE_CHURN = [
    "sla_cumprido", "uso_plataforma", "media_reclamacoes", "atraso_pagamento",
    "tempo_medio_resolucao", "taxa_reabertura", "ticket_medio",
]


def analisar_fatores_churn() -> dict:
    """
    Compara a média de cada métrica entre clientes ativos e cancelados, e
    ranqueia pela maior diferença relativa — é a tool `analisar_fatores_churn`,
    pra perguntas tipo "o que mais influencia o cancelamento". Cálculo real
    (reaproveita calcular_metrica duas vezes, uma por grupo); a IA só lê o
    ranking e formata, nunca infere a correlação sozinha.
    """
    ranking = []
    for metrica_id in _METRICAS_PARA_ANALISE_CHURN:
        ativos = calcular_metrica(metrica_id, {"situacao": "Ativo"})
        cancelados = calcular_metrica(metrica_id, {"situacao": "Cancelado"})
        if "valor" not in ativos or "valor" not in cancelados:
            continue
        v_ativos = ativos["valor"]
        v_cancelados = cancelados["valor"]
        base = abs(v_ativos) if v_ativos else 1
        diferenca_percentual = round((v_cancelados - v_ativos) / base * 100, 1)
        ranking.append({
            "metrica": metrica_id,
            "rotulo": ativos["rotulo"],
            "valor_clientes_ativos": v_ativos,
            "valor_clientes_cancelados": v_cancelados,
            "diferenca_percentual": diferenca_percentual,
        })

    # chamados_criticos entra como MÉDIA por cliente-mês (não a soma que o
    # catálogo normal usa) — ver nota acima sobre viés de tamanho de amostra.
    df_ativos = _filtrar("atendimento_mensal", {"situacao": "Ativo"})
    df_cancelados = _filtrar("atendimento_mensal", {"situacao": "Cancelado"})
    media_criticos_ativos = _media(df_ativos["chamados_criticos"])
    media_criticos_cancelados = _media(df_cancelados["chamados_criticos"])
    if media_criticos_ativos is not None and media_criticos_cancelados is not None:
        base = abs(media_criticos_ativos) if media_criticos_ativos else 1
        ranking.append({
            "metrica": "chamados_criticos_media",
            "rotulo": "Chamados críticos (média por cliente-mês)",
            "valor_clientes_ativos": round(media_criticos_ativos, 4),
            "valor_clientes_cancelados": round(media_criticos_cancelados, 4),
            "diferenca_percentual": round((media_criticos_cancelados - media_criticos_ativos) / base * 100, 1),
        })

    # NPS tem estrutura própria (score + nota_media) — compara pela nota média.
    nps_ativos = calcular_metrica("nps", {"situacao": "Ativo"})
    nps_cancelados = calcular_metrica("nps", {"situacao": "Cancelado"})
    if "nota_media" in nps_ativos and "nota_media" in nps_cancelados:
        v_ativos = nps_ativos["nota_media"]
        v_cancelados = nps_cancelados["nota_media"]
        base = abs(v_ativos) if v_ativos else 1
        ranking.append({
            "metrica": "nps",
            "rotulo": "NPS (nota média)",
            "valor_clientes_ativos": round(v_ativos, 2),
            "valor_clientes_cancelados": round(v_cancelados, 2),
            "diferenca_percentual": round((v_cancelados - v_ativos) / base * 100, 1),
        })

    ranking.sort(key=lambda r: abs(r["diferenca_percentual"]), reverse=True)

    return {
        "universo": "Comparando clientes Ativos (58) vs Cancelados (22), 80 clientes no total.",
        "ranking_por_maior_diferenca": ranking,
        "nota": (
            "diferenca_percentual é (cancelados - ativos) / ativos, em %. "
            "Positivo = maior entre cancelados; negativo = menor entre cancelados. "
            "Isso mostra associação, não prova causa."
        ),
    }


# --- Tool: clientes_em_risco ------------------------------------------------
# Porta a mesma lógica de src/engine/inovaappsDatabase.js#calcularRisco: en
# vez de comparar com a média da carteira, compara o mês mais recente de
# CADA cliente com a própria média histórica dele — evita falso alarme em
# quem sempre operou "abaixo da média" mas nunca piorou de verdade.

def _serie_valida(valores):
    limpos = [v for v in valores if v is not None and v == v]  # v == v descarta NaN
    if not limpos:
        return None
    return sum(limpos) / len(limpos)


def _calcular_risco_cliente(cliente_id: str) -> dict | None:
    historico = dados.atendimento_mensal[dados.atendimento_mensal["cliente_id"] == cliente_id].sort_values("mes_ref")
    if len(historico) < 2:
        return None

    atual = historico.iloc[-1]
    anteriores = historico.iloc[:-1]

    baseline_sla = _serie_valida(anteriores["pct_sla_cumprido"].tolist())
    baseline_uso = _serie_valida(anteriores["uso_plataforma_pct"].tolist())
    baseline_atraso = _serie_valida(anteriores["dias_atraso_pagamento"].tolist())

    sinais = []
    if baseline_sla is not None and atual["pct_sla_cumprido"] == atual["pct_sla_cumprido"] and atual["pct_sla_cumprido"] < baseline_sla - 10:
        sinais.append("Queda no SLA cumprido")
    if baseline_uso is not None and atual["uso_plataforma_pct"] < baseline_uso - 10:
        sinais.append("Queda no uso da plataforma")
    if baseline_atraso is not None and atual["dias_atraso_pagamento"] > baseline_atraso + 3:
        sinais.append("Atraso de pagamento crescente")
    if atual["chamados_criticos"] >= 2:
        sinais.append("Mais chamados críticos")
    if atual["chamados_reabertos"] >= 2:
        sinais.append("Mais chamados reabertos")
    if atual["reunioes_previstas"] == 1 and atual["reunioes_realizadas"] == 0:
        sinais.append("Reunião prevista não realizada")
    if atual["reclamacoes_formais"] >= 1:
        sinais.append("Reclamação formal recente")

    respostas_nps = dados.pesquisas_nps[
        (dados.pesquisas_nps["cliente_id"] == cliente_id) & (dados.pesquisas_nps["respondeu"] == 1)
    ].sort_values("mes_ref")
    if len(respostas_nps) > 0 and respostas_nps.iloc[-1]["classificacao_nps"] == "Detrator":
        sinais.append("NPS detrator")

    nivel = "Baixo"
    if len(sinais) >= 4:
        nivel = "Alto"
    elif len(sinais) >= 2:
        nivel = "Médio"

    return {"cliente_id": cliente_id, "nivel": nivel, "sinais": sinais, "mes_ref": atual["mes_ref"]}


def clientes_em_risco(nivel: str = "Alto") -> dict:
    """Lista clientes ativos num nível de risco — pra perguntas tipo 'quais
    clientes estão em risco' ou 'quem eu devo ligar primeiro'."""
    if nivel not in ("Alto", "Médio", "Baixo"):
        nivel = "Alto"

    ativos = dados.situacao_clientes[dados.situacao_clientes["situacao"] == "Ativo"]["cliente_id"].tolist()
    encontrados = []
    for cliente_id in ativos:
        risco = _calcular_risco_cliente(cliente_id)
        if risco and risco["nivel"] == nivel:
            encontrados.append(risco)

    return {
        "nivel": nivel,
        "total_clientes_ativos": len(ativos),
        "clientes_encontrados": len(encontrados),
        "clientes": encontrados,
    }
