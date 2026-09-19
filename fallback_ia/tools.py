"""
Schema das tools expostas à Claude API — igual ao definido no prompt de
fallback, ligado às mesmas funções que já resolvem o catálogo determinístico
(metricas.py / registro_cliente.py). Nenhuma lógica de cálculo mora aqui:
este módulo só descreve a interface e roteia pra quem já sabe calcular.
"""
from __future__ import annotations

from . import metricas, registro_cliente

TOOLS = [
    {
        "name": "consultar_metrica",
        "description": (
            "Calcula uma métrica agregada sobre a base de clientes "
            "(ticket médio, tempo de resolução, reclamações, atraso de "
            "pagamento, SLA, NPS, churn, uso da plataforma, reuniões, "
            "chamados críticos, taxa de reabertura), com filtros opcionais."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {
                    "type": "string",
                    "enum": [
                        "ticket_medio", "tempo_medio_resolucao", "media_reclamacoes",
                        "atraso_pagamento", "sla_cumprido", "nps", "churn",
                        "uso_plataforma", "reunioes_realizadas", "chamados_criticos",
                        "taxa_reabertura",
                    ],
                    "description": "Qual métrica calcular.",
                },
                "filtros": {
                    "type": "object",
                    "properties": {
                        "plano": {"type": "string", "enum": ["Essencial", "Avancado", "Enterprise"]},
                        "porte": {"type": "string", "enum": ["Pequeno", "Medio", "Grande"]},
                        "segmento": {"type": "string"},
                        "situacao": {"type": "string", "enum": ["Ativo", "Cancelado"]},
                        "periodo_inicio": {"type": "string", "description": "AAAA-MM"},
                        "periodo_fim": {"type": "string", "description": "AAAA-MM"},
                        "cliente_id": {"type": "string"},
                    },
                },
            },
            "required": ["metrica"],
        },
    },
    {
        "name": "buscar_registro_cliente",
        "description": (
            "Busca informações pontuais de um cliente específico: último "
            "acompanhamento, situação do contrato, plano atual, histórico "
            "recente de chamados ou NPS."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "ID do cliente, ex: C007"},
                "campo": {
                    "type": "string",
                    "enum": [
                        "ultimo_acompanhamento", "situacao", "plano",
                        "historico_chamados", "historico_nps",
                    ],
                },
            },
            "required": ["cliente_id", "campo"],
        },
    },
]


def executar_tool(nome: str, entrada: dict) -> dict:
    """Roda a consulta de verdade contra os dados reais. Nunca retorna texto
    livre — sempre um dict estruturado que a Claude só pode reformatar."""
    if nome == "consultar_metrica":
        return metricas.calcular_metrica(entrada.get("metrica"), entrada.get("filtros") or {})
    if nome == "buscar_registro_cliente":
        return registro_cliente.buscar_registro_cliente(entrada.get("cliente_id"), entrada.get("campo"))
    return {"erro": f"Tool desconhecida: {nome}"}
