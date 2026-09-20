"""
Fatores de cancelamento: o que difere entre clientes ativos e cancelados.

Compara a média de cada métrica entre os dois grupos e ranqueia pela maior
diferença relativa. É de onde saem os **pesos** do índice de alerta — os
pesos não são chutados, vêm daqui.

Havia duas fórmulas no repo para responder esta mesma pergunta: esta
(contraste de médias) e uma correlação de Pearson, em `churn.py`. Esta
venceu por não alterar nenhum número já validado; a de Pearson deixou de
existir em paralelo, e o script de exploração passou a chamar esta função.
"""
from __future__ import annotations

from ..metricas import agregacoes as ag
from ..metricas.resolvedor import calcular_metrica, filtrar

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
METRICAS_PARA_ANALISE = [
    "sla_cumprido", "uso_plataforma", "media_reclamacoes", "atraso_pagamento",
    "tempo_medio_resolucao", "taxa_reabertura", "ticket_medio", "reunioes_realizadas",
]


def _universo() -> str:
    """Contado dos dados, não escrito à mão. Antes era a string fixa
    "Ativos (58) vs Cancelados (22), 80 clientes" — que passaria a mentir no
    dia em que a base mudasse."""
    from holder.infra.dados import carteira

    situacao = carteira.aba("situacao_clientes")
    ativos = int((situacao["situacao"] == "Ativo").sum())
    cancelados = int((situacao["situacao"] == "Cancelado").sum())
    return (
        f"Comparando clientes Ativos ({ativos}) vs Cancelados ({cancelados}), "
        f"{len(situacao)} clientes no total."
    )


def analisar_fatores_churn() -> dict:
    """
    Compara a média de cada métrica entre clientes ativos e cancelados, e
    ranqueia pela maior diferença relativa — é a tool `analisar_fatores_churn`,
    pra perguntas tipo "o que mais influencia o cancelamento". Cálculo real
    (reaproveita calcular_metrica duas vezes, uma por grupo); a IA só lê o
    ranking e formata, nunca infere a correlação sozinha.
    """
    ranking = []
    for metrica_id in METRICAS_PARA_ANALISE:
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
    df_ativos = filtrar("atendimento_mensal", {"situacao": "Ativo"})
    df_cancelados = filtrar("atendimento_mensal", {"situacao": "Cancelado"})
    media_criticos_ativos = ag.media(df_ativos["chamados_criticos"])
    media_criticos_cancelados = ag.media(df_cancelados["chamados_criticos"])
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
        "universo": _universo(),
        "ranking_por_maior_diferenca": ranking,
        "nota": (
            "diferenca_percentual é (cancelados - ativos) / ativos, em %. "
            "Positivo = maior entre cancelados; negativo = menor entre cancelados. "
            "Isso mostra associação, não prova causa."
        ),
    }
