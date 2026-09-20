"""
Strikes — a **predição por semelhança**.

Compara o cliente ativo com o padrão real de comportamento de quem já
cancelou nos meses antes de sair: "este cliente hoje se parece com como os
que cancelaram estavam pouco antes de cancelar?". Cada linha de corte batida
é um strike.

É conceito distinto do índice de alerta (`holder/dominio/alerta/`), que
compara o cliente com a própria história. Ver `CONTEXT.md`.

É sempre um fato sobre o passado (quem já cancelou) aplicado ao presente de
quem ainda está ativo — nunca uma estimativa inventada. O modelo de IA só
formata o resultado deste cálculo, como em todo o resto do projeto.
"""
from __future__ import annotations

from holder.infra.dados import carteira

from ..metricas.resolvedor import filtrar
from .benchmark import linhas_de_corte
from .recencia import meses_recentes

SINAIS = ("SLA crítico atual", "Lentidão de resolução atual", "Reclamação recente", "Último NPS detrator")


def prever_risco_cancelamento(cliente_id: str | None = None, limite: int = 20) -> dict:
    """
    Prevê quais clientes ativos têm hoje um padrão parecido com o de
    clientes que já cancelaram (SLA crítico, lentidão, reclamação recente,
    NPS detrator) — cada sinal batido vira um "strike". Sem cliente_id,
    lista os ativos com pelo menos 1 strike, ordenados do pior pro melhor;
    com cliente_id, avalia só aquele cliente.

    O nome desta função ainda fala "risco"; ele muda na fase 8, junto com o
    texto de tela e as descrições das tools.
    """
    linhas = linhas_de_corte()
    if not linhas:
        return {"erro": "Sem clientes cancelados suficientes na base pra montar o padrão de comparação."}

    df_ativos_atd = filtrar("atendimento_mensal", {"situacao": "Ativo"})
    if cliente_id:
        cliente_id = carteira.normalizar_cliente_id(cliente_id)
        if not carteira.cliente_existe(cliente_id) or carteira.situacao_do_cliente(cliente_id) != "Ativo":
            return {"erro": f"Cliente {cliente_id} não encontrado entre os ativos."}

    # taxa_disparo_por_sinal precisa da população TODA de ativos como base,
    # mesmo quando cliente_id filtra o resultado pra um só — por isso o
    # loop abaixo sempre roda sobre TODOS os ativos (df_ativos_atd), e só no
    # final filtramos pro cliente pedido; senão a taxa viraria 100%/0%
    # degenerada (base de 1 cliente) em vez da taxa real da carteira.
    janela = meses_recentes(df_ativos_atd)

    pesquisas = carteira.aba("pesquisas_nps")
    total_ativos_avaliados = df_ativos_atd["cliente_id"].nunique()
    contagem_por_sinal = {sinal: 0 for sinal in SINAIS}
    resultados = []

    for cid, grupo in df_ativos_atd.groupby("cliente_id"):
        grupo = grupo.sort_values("mes_ref")
        ultima_linha = grupo.iloc[-1]

        ultima_nps = pesquisas[
            (pesquisas["cliente_id"] == cid) & (pesquisas["respondeu"] == 1)
        ].sort_values("mes_ref")
        classificacao_nps_recente = ultima_nps.iloc[-1]["classificacao_nps"] if len(ultima_nps) > 0 else None

        reclamacoes_recentes = grupo[grupo["mes_ref"].isin(janela)]["reclamacoes_formais"].sum()

        strikes = []
        if "pct_sla_cumprido" in linhas and ultima_linha["pct_sla_cumprido"] == ultima_linha["pct_sla_cumprido"] and ultima_linha["pct_sla_cumprido"] <= linhas["pct_sla_cumprido"]:
            strikes.append("SLA crítico atual")
        if "tempo_medio_resolucao_h" in linhas and ultima_linha["tempo_medio_resolucao_h"] >= linhas["tempo_medio_resolucao_h"]:
            strikes.append("Lentidão de resolução atual")
        if reclamacoes_recentes > 0:
            strikes.append("Reclamação recente")
        if classificacao_nps_recente == "Detrator":
            strikes.append("Último NPS detrator")

        for sinal in strikes:
            contagem_por_sinal[sinal] += 1

        if strikes:
            resultados.append({
                "cliente_id": cid,
                "strikes": strikes,
                "total_strikes": len(strikes),
                "mes_ref": ultima_linha["mes_ref"],
            })

    resultados.sort(key=lambda r: r["total_strikes"], reverse=True)

    # Taxa de disparo de cada sinal sobre TODOS os ativos avaliados (não só
    # os que tiveram algum strike) — sinal que dispara pra quase todo mundo
    # é fraco isoladamente (alto risco de falso alarme).
    taxa_disparo_por_sinal = {
        sinal: round(qtd / total_ativos_avaliados * 100, 1) if total_ativos_avaliados else 0.0
        for sinal, qtd in contagem_por_sinal.items()
    }

    if cliente_id:
        resultado_cliente = next((r for r in resultados if r["cliente_id"] == cliente_id), None)
        if not resultado_cliente:
            return {
                "cliente_id": cliente_id,
                "total_strikes": 0,
                "strikes": [],
                "predicao": "Nenhum sinal de alerta — o cliente não se parece com o padrão de quem cancelou.",
            }
        return {**resultado_cliente, "taxa_disparo_por_sinal": taxa_disparo_por_sinal}

    limite = max(1, min(limite or 20, 100))
    return {
        "total_clientes_ativos": total_ativos_avaliados,
        "clientes_com_alerta": len(resultados),
        "clientes": resultados[:limite],
        "truncado": len(resultados) > limite,
        "linhas_de_corte": {k: round(v, 2) for k, v in linhas.items()},
        "taxa_disparo_por_sinal": taxa_disparo_por_sinal,
        "nota": (
            "Predição baseada no padrão real de comportamento de clientes que já "
            "cancelaram (últimos meses antes de sair) — não é um diagnóstico do "
            "histórico do próprio cliente (isso é a tool clientes_em_risco). Um "
            "sinal com taxa_disparo_por_sinal alta dispara pra muitos clientes "
            "ativos — sozinho é fraco, mas vários strikes juntos no mesmo "
            "cliente são um alerta forte."
        ),
    }
