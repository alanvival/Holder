"""
Valida o port Python do motor de métricas contra os mesmos valores de
referência do prompt de métricas (espelha
assistente-consultas/scripts/testar-metricas.mjs) — garante que a tool
`consultar_metrica` que a Claude vai chamar calcula exatamente igual ao
catálogo determinístico em JS.

Uso: python -m fallback_ia.testar_metricas
"""
from .metricas import calcular_metrica

falhas = 0
total = 0


def checar(descricao, obtido, esperado, tolerancia=0.05):
    global falhas, total
    total += 1
    ok = obtido is not None and abs(obtido - esperado) <= tolerancia
    if ok:
        print(f"OK   {descricao}: {obtido:.4f} (esperado {esperado})")
    else:
        falhas += 1
        print(f"FAIL {descricao}: obtido {obtido} — esperado {esperado}")


checar("Ticket médio — base completa (80)", calcular_metrica("ticket_medio")["valor"], 12287.05)
checar("Ticket médio — só ativos (58)", calcular_metrica("ticket_medio", {"situacao": "Ativo"})["valor"], 12206.86)
checar("Ticket médio — Essencial", calcular_metrica("ticket_medio", {"plano": "Essencial"})["valor"], 3299.14)
checar("Ticket médio — Avançado", calcular_metrica("ticket_medio", {"plano": "Avancado"})["valor"], 10629.96)
checar("Ticket médio — Enterprise", calcular_metrica("ticket_medio", {"plano": "Enterprise"})["valor"], 31111.32)

checar("Tempo médio de resolução — ponderado", calcular_metrica("tempo_medio_resolucao")["valor"], 23.21, 0.1)
checar("Média de reclamações", calcular_metrica("media_reclamacoes")["valor"], 0.402, 0.005)
checar("Atraso médio de pagamento", calcular_metrica("atraso_pagamento")["valor"], 3.18, 0.05)
checar("SLA cumprido — ponderado", calcular_metrica("sla_cumprido")["valor"], 75.96, 0.2)

nps = calcular_metrica("nps")
checar("NPS — score", nps.get("score"), -6.8, 0.3)
checar("NPS — nota média", nps.get("nota_media"), 7.11, 0.05)

checar("Taxa de cancelamento", calcular_metrica("churn")["valor"], 27.5, 0.1)
checar("Uso médio da plataforma", calcular_metrica("uso_plataforma")["valor"], 79.81, 0.1)
checar("Reuniões realizadas", calcular_metrica("reunioes_realizadas")["valor"], 76.9, 0.1)
checar("Chamados críticos — total", calcular_metrica("chamados_criticos")["valor"], 1016, 0.5)
checar("Taxa de reabertura", calcular_metrica("taxa_reabertura")["valor"], 12.23, 0.1)

print(f"\n{total - falhas}/{total} testes passaram.")
if falhas:
    raise SystemExit(1)
