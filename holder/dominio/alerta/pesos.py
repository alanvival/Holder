"""
Peso de cada sinal de alerta.

Os pesos **não são chutados**: vêm dos fatores de cancelamento, ou seja, do
quanto cada indicador difere entre clientes ativos e cancelados na base
real. Um sinal que historicamente separa melhor quem cancelou de quem ficou
pesa mais.

São recalculados a cada chamada, de propósito, pra nunca dessincronizar do
dado. O lado JavaScript tem esses mesmos pesos escritos à mão, com um
comentário admitindo que a sincronia é manual — isso é o que a fase 7
resolve, passando a gerá-los daqui.
"""
from __future__ import annotations

from ..churn.fatores import analisar_fatores_churn


def pesos_dos_sinais() -> dict[str, int]:
    """Pontuação de cada sinal (estilo credit score: soma ponderada, não
    contagem simples, porque os sinais não valem a mesma coisa)."""
    fatores = {
        item["metrica"]: abs(item["diferenca_percentual"])
        for item in analisar_fatores_churn()["ranking_por_maior_diferenca"]
    }

    def peso(chave: str, minimo: int = 1) -> int:
        # Guarda deliberada: se um id de métrica mudar e esta chave deixar
        # de existir, o peso cairia pro mínimo em SILÊNCIO e o índice de
        # alerta inteiro mudaria de valor sem ninguém notar. Melhor falhar.
        if chave not in fatores:
            raise KeyError(
                f"Fator de cancelamento '{chave}' não existe no ranking — "
                f"algum id de métrica mudou sem atualizar os pesos. "
                f"Disponíveis: {sorted(fatores)}"
            )
        return max(minimo, round(fatores[chave]))

    return {
        "Mais chamados críticos": peso("chamados_criticos_media"),
        "Reclamação formal recente": peso("media_reclamacoes"),
        "Atraso de pagamento crescente": peso("atraso_medio_pagamento"),
        "NPS detrator": peso("nps_carteira"),
        "Mais chamados reabertos": peso("taxa_reabertura"),
        "Queda no SLA cumprido": peso("sla_cumprido"),
        "Queda no uso da plataforma": peso("uso_medio_plataforma"),
        "Reunião prevista não realizada": peso("reunioes_realizadas"),
    }
