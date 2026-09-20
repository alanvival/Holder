"""
As faixas de ação do score de risco.

Quatro nomes, e são exclusivos deste conceito: o índice de alerta usa
Alto/Médio/Baixo justamente para não colidir com estes. Ver `CONTEXT.md`.
"""
from __future__ import annotations

# Ponto de partida, a recalibrar quando houver histórico real de quantos
# clientes em cada faixa efetivamente cancelaram.
FAIXAS = [
    (0, 30, "Saudável"),
    (30, 55, "Atenção"),
    (55, 75, "Em risco"),
    (75, 101, "Crítico"),
]

NOMES = [nome for _, _, nome in FAIXAS]

# Ação sugerida por faixa — texto fixo e auditável, não a IA "decidindo"
# sozinha o que recomendar a cada resposta. Única fonte: era duplicado em
# holder/aplicacao/assistente/previsao_risco.py (a IA) e precisa aparecer
# igual no dashboard, senão as duas telas recomendam coisas diferentes pro
# mesmo cliente na mesma faixa.
ACAO_POR_FAIXA = {
    "Saudável": "Nenhuma ação necessária — monitoramento passivo.",
    "Atenção": "Sinalizar no radar do CS responsável, sem alerta ativo ainda — acompanhar a tendência do próximo mês.",
    "Em risco": "Alerta ativo: o CS deve investigar a causa e agendar contato proativo com o cliente.",
    "Crítico": "Alerta prioritário — ação imediata: contato executivo, plano de retenção e revisão do relacionamento nos próximos dias.",
}


def faixa_de(risco_percentual: float) -> str:
    for lo, hi, nome in FAIXAS:
        if lo <= risco_percentual < hi:
            return nome
    return "Crítico"


def arredondar(v):
    """Duas casas, tratando None e NaN (`v != v` é verdade só para NaN)."""
    if v is None or v != v:
        return None
    return round(float(v), 2)
