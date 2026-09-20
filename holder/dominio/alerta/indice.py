"""
Índice de alerta — o **diagnóstico**.

Compara o mês mais recente de cada cliente com a **própria média histórica
dele**, não com a média da carteira. É isso que evita falso alarme em quem
sempre operou "abaixo da média" mas nunca piorou de verdade.

Responde "este cliente piorou?". É conceito distinto dos strikes
(`holder/dominio/strikes/`), que perguntam "este cliente se parece com quem
já cancelou?" — um cliente sempre-ruim-mas-estável dispara strikes e não
dispara índice de alerta; um cliente ótimo que piorou de repente dispara o
índice e pode não disparar strike nenhum. Ver `CONTEXT.md`.

Escala própria: Alto / Médio / Baixo, para não colidir com as quatro faixas
do score de risco.
"""
from __future__ import annotations

from holder.infra.dados import carteira

from ..metricas import agregacoes as ag
from .pesos import pesos_dos_sinais

LIMITE_ALTO = 50
LIMITE_MEDIO = 20


def _calcular_para_cliente(cliente_id: str, pesos: dict[str, int]) -> dict | None:
    atendimento = carteira.aba("atendimento_mensal")
    historico = atendimento[atendimento["cliente_id"] == cliente_id].sort_values("mes_ref")
    if len(historico) < 2:
        return None

    atual = historico.iloc[-1]
    anteriores = historico.iloc[:-1]

    baseline_sla = ag.media_de_lista(anteriores["pct_sla_cumprido"].tolist())
    baseline_uso = ag.media_de_lista(anteriores["uso_plataforma_pct"].tolist())
    baseline_atraso = ag.media_de_lista(anteriores["dias_atraso_pagamento"].tolist())

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

    pesquisas = carteira.aba("pesquisas_nps")
    respostas_nps = pesquisas[
        (pesquisas["cliente_id"] == cliente_id) & (pesquisas["respondeu"] == 1)
    ].sort_values("mes_ref")
    if len(respostas_nps) > 0 and respostas_nps.iloc[-1]["classificacao_nps"] == "Detrator":
        sinais.append("NPS detrator")

    pontuacao = sum(pesos[s] for s in sinais)
    pontuacao_maxima = sum(pesos.values())
    percentual = pontuacao / pontuacao_maxima * 100

    nivel = "Baixo"
    if percentual >= LIMITE_ALTO:
        nivel = "Alto"
    elif percentual >= LIMITE_MEDIO:
        nivel = "Médio"

    return {
        "cliente_id": cliente_id,
        "nivel": nivel,
        "pontuacao_risco": pontuacao,
        "pontuacao_maxima": pontuacao_maxima,
        "sinais": sinais,
        "mes_ref": atual["mes_ref"],
    }


def clientes_em_risco(nivel: str = "Alto") -> dict:
    """Lista clientes ativos num nível de alerta — pra perguntas tipo 'quais
    clientes estão em risco' ou 'quem eu devo ligar primeiro'. O nível vem de
    uma pontuação ponderada (ver `pesos.py`), não de contar sinais como se
    todos pesassem igual.

    O nome desta função ainda fala "risco"; ele muda na fase 8, junto com o
    texto de tela e as descrições das tools."""
    if nivel not in ("Alto", "Médio", "Baixo"):
        nivel = "Alto"

    pesos = pesos_dos_sinais()
    situacao = carteira.aba("situacao_clientes")
    ativos = situacao[situacao["situacao"] == "Ativo"]["cliente_id"].tolist()

    encontrados = []
    for cliente_id in ativos:
        indice = _calcular_para_cliente(cliente_id, pesos)
        if indice and indice["nivel"] == nivel:
            encontrados.append(indice)

    encontrados.sort(key=lambda r: r["pontuacao_risco"], reverse=True)
    return {
        "nivel": nivel,
        "total_clientes_ativos": len(ativos),
        "clientes_encontrados": len(encontrados),
        "pesos_sinais": pesos,
        "clientes": encontrados,
    }
