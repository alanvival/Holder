"""
Valida o motor de métricas em Python contra os mesmos valores de referência
conferidos no lado JavaScript (interface do assistente, `npm run
test:metricas`). É o lado Python do teste de contrato: os dois resolvedores
calculam a partir da mesma definição, e estes números provam que concordam.

Era um script com `print` + `SystemExit(1)` que rodava no import (não tinha
`__main__`); virou pytest com asserção real, sem mudar um único valor
esperado nem uma tolerância.

Uso: pytest testes/test_metricas.py

Nota: os ids usados aqui (`atraso_pagamento`, `churn`, `uso_plataforma`,
`nps`) são os atuais do lado Python. A fase 7 os converge para os ids do
JavaScript (`atraso_medio_pagamento`, `taxa_cancelamento`,
`uso_medio_plataforma`, `nps_carteira`), e este arquivo acompanha.
"""
import pytest

from fallback_ia.metricas import calcular_metrica

# (descrição, métrica, filtros, esperado, tolerância)
CASOS = [
    ("ticket médio — base completa (80)", "ticket_medio", None, 12287.05, 0.05),
    ("ticket médio — só ativos (58)", "ticket_medio", {"situacao": "Ativo"}, 12206.86, 0.05),
    ("ticket médio — Essencial", "ticket_medio", {"plano": "Essencial"}, 3299.14, 0.05),
    ("ticket médio — Avançado", "ticket_medio", {"plano": "Avancado"}, 10629.96, 0.05),
    ("ticket médio — Enterprise", "ticket_medio", {"plano": "Enterprise"}, 31111.32, 0.05),
    ("tempo médio de resolução — ponderado", "tempo_medio_resolucao", None, 23.21, 0.1),
    ("média de reclamações", "media_reclamacoes", None, 0.402, 0.005),
    ("atraso médio de pagamento", "atraso_pagamento", None, 3.18, 0.05),
    ("SLA cumprido — ponderado", "sla_cumprido", None, 75.96, 0.2),
    ("taxa de cancelamento", "churn", None, 27.5, 0.1),
    ("uso médio da plataforma", "uso_plataforma", None, 79.81, 0.1),
    ("reuniões realizadas", "reunioes_realizadas", None, 76.9, 0.1),
    ("chamados críticos — total", "chamados_criticos", None, 1016, 0.5),
    ("taxa de reabertura", "taxa_reabertura", None, 12.23, 0.1),
]


@pytest.mark.parametrize(
    "metrica,filtros,esperado,tolerancia",
    [(c[1], c[2], c[3], c[4]) for c in CASOS],
    ids=[c[0] for c in CASOS],
)
def test_valor_da_metrica(metrica, filtros, esperado, tolerancia):
    obtido = calcular_metrica(metrica, filtros)["valor"]
    assert obtido is not None, f"métrica '{metrica}' devolveu valor nulo"
    assert abs(obtido - esperado) <= tolerancia, (
        f"métrica '{metrica}': obtido {obtido:.4f}, esperado {esperado} "
        f"(tolerância {tolerancia})"
    )


def test_nps_da_carteira():
    """O NPS devolve um dicionário, não um `valor` — score e nota média são
    conferidos separadamente."""
    nps = calcular_metrica("nps")

    assert nps.get("score") is not None, "NPS sem score"
    assert abs(nps["score"] - (-6.8)) <= 0.3, f"NPS score: obtido {nps['score']}, esperado -6.8"

    assert nps.get("nota_media") is not None, "NPS sem nota média"
    assert abs(nps["nota_media"] - 7.11) <= 0.05, (
        f"NPS nota média: obtido {nps['nota_media']}, esperado 7.11"
    )
