"""
Schema das tools expostas ao provedor de IA (formato Anthropic —
`input_schema` — que é a fonte da verdade), ligado às mesmas funções que já
resolvem o catálogo determinístico (metricas.py / registro_cliente.py).
Nenhuma lógica de cálculo mora aqui: este módulo só descreve a interface e
roteia pra quem já sabe calcular. `tools_formato_openai()` converte pro
formato usado pela Groq/OpenAI (`function.parameters`), sem duplicar o
schema — um só lugar descreve as tools, cada provedor só lê num formato
diferente.
"""
from __future__ import annotations

from . import metricas, registro_cliente

# Reaproveitado em várias tools — mesmo shape de recorte em todo lugar.
_FILTROS_SCHEMA = {
    "type": "object",
    "properties": {
        "plano": {"type": "string", "enum": ["Essencial", "Avancado", "Enterprise"]},
        "porte": {"type": "string", "enum": ["Pequeno", "Medio", "Grande"]},
        "segmento": {"type": "string"},
        "situacao": {"type": "string", "enum": ["Ativo", "Cancelado"]},
        "periodo_inicio": {"type": "string", "description": "AAAA-MM"},
        "periodo_fim": {"type": "string", "description": "AAAA-MM"},
    },
}

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
        "name": "analisar_fatores_churn",
        "description": (
            "Compara os indicadores médios entre clientes ativos e "
            "cancelados (SLA, uso da plataforma, reclamações, atraso de "
            "pagamento, tempo de resolução, chamados críticos, taxa de "
            "reabertura, ticket médio, NPS) e devolve um ranking de qual "
            "métrica mais difere entre os dois grupos. Use pra perguntas "
            "tipo 'o que mais influencia o cancelamento', 'quais fatores "
            "levam ao churn', 'o que diferencia quem cancela de quem fica'. "
            "Não tem parâmetros — sempre compara a carteira inteira."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "ranking_clientes",
        "description": (
            "Lista os clientes com maior ou menor valor numa métrica "
            "específica — use pra perguntas tipo 'qual cliente tem o maior "
            "ticket', 'quais clientes têm o pior SLA', 'quem tem mais "
            "chamados críticos', 'top 5 clientes por uso da plataforma'. "
            "Diferente de consultar_metrica (que devolve UM número agregado "
            "de toda a carteira), esta tool devolve uma LISTA de clientes "
            "individuais ordenada. Não suporta as métricas 'churn' nem "
            "'nps' (não fazem sentido por cliente individual nesse formato)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {
                    "type": "string",
                    "enum": [
                        "ticket_medio", "tempo_medio_resolucao", "media_reclamacoes",
                        "atraso_pagamento", "sla_cumprido", "uso_plataforma",
                        "reunioes_realizadas", "chamados_criticos", "taxa_reabertura",
                    ],
                    "description": "Qual métrica usar pra ordenar os clientes.",
                },
                "direcao": {
                    "type": "string",
                    "enum": ["maior", "menor"],
                    "description": "'maior' = do maior valor pro menor (topo do ranking); 'menor' = do menor pro maior.",
                },
                "quantidade": {"type": "integer", "description": "Quantos clientes retornar (padrão 5)."},
                "filtros": _FILTROS_SCHEMA,
            },
            "required": ["metrica"],
        },
    },
    {
        "name": "contar_clientes",
        "description": (
            "Conta quantos clientes batem com um conjunto de filtros — use "
            "pra perguntas tipo 'quantos clientes tem o plano Enterprise', "
            "'quantos clientes ativos no segmento Varejo'. Sem filtros, "
            "conta a carteira inteira."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"filtros": _FILTROS_SCHEMA},
        },
    },
    {
        "name": "evolucao_metrica",
        "description": (
            "Série mensal de uma métrica ao longo do tempo — use pra "
            "perguntas tipo 'como o SLA evoluiu nos últimos meses', 'a "
            "carteira está melhorando ou piorando', 'tendência de uso da "
            "plataforma'. Não suporta 'ticket_medio', 'churn' nem 'nps' "
            "(não variam mês a mês da mesma forma nesta base)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {
                    "type": "string",
                    "enum": [
                        "tempo_medio_resolucao", "media_reclamacoes", "atraso_pagamento",
                        "sla_cumprido", "uso_plataforma", "reunioes_realizadas",
                        "chamados_criticos", "taxa_reabertura",
                    ],
                },
                "filtros": _FILTROS_SCHEMA,
            },
            "required": ["metrica"],
        },
    },
    {
        "name": "comparar_por_categoria",
        "description": (
            "Compara uma métrica entre as categorias de plano, porte ou "
            "segmento — use pra perguntas tipo 'qual segmento tem mais "
            "churn', 'compare os planos por SLA', 'qual porte reclama mais'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {
                    "type": "string",
                    "enum": [
                        "ticket_medio", "tempo_medio_resolucao", "media_reclamacoes",
                        "atraso_pagamento", "sla_cumprido", "churn", "uso_plataforma",
                        "reunioes_realizadas", "chamados_criticos", "taxa_reabertura",
                    ],
                },
                "categoria": {"type": "string", "enum": ["plano", "porte", "segmento"]},
                "filtros": _FILTROS_SCHEMA,
            },
            "required": ["metrica", "categoria"],
        },
    },
    {
        "name": "clientes_em_risco",
        "description": (
            "Lista clientes ativos classificados num nível de risco de "
            "cancelamento (Alto, Médio ou Baixo), calculado comparando o "
            "mês mais recente de cada cliente com a própria média "
            "histórica dele (não com a média da carteira). Use pra "
            "perguntas tipo 'quais clientes estão em risco', 'quem eu "
            "devo ligar primeiro', 'quais contas estão em perigo'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nivel": {
                    "type": "string",
                    "enum": ["Alto", "Médio", "Baixo"],
                    "description": "Nível de risco a listar. Padrão: Alto.",
                },
            },
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


def tools_formato_openai() -> list[dict]:
    """Groq (e qualquer API compatível com OpenAI) espera
    {"type": "function", "function": {name, description, parameters}} em
    vez de {name, description, input_schema} — só reembala, mesmo schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOLS
    ]


def executar_tool(nome: str, entrada: dict) -> dict:
    """Roda a consulta de verdade contra os dados reais. Nunca retorna texto
    livre — sempre um dict estruturado que a Claude só pode reformatar."""
    if nome == "consultar_metrica":
        return metricas.calcular_metrica(entrada.get("metrica"), entrada.get("filtros") or {})
    if nome == "analisar_fatores_churn":
        return metricas.analisar_fatores_churn()
    if nome == "ranking_clientes":
        return metricas.ranking_clientes(
            entrada.get("metrica"), entrada.get("direcao", "maior"),
            entrada.get("quantidade", 5), entrada.get("filtros") or {},
        )
    if nome == "contar_clientes":
        return metricas.contar_clientes(entrada.get("filtros") or {})
    if nome == "evolucao_metrica":
        return metricas.evolucao_metrica(entrada.get("metrica"), entrada.get("filtros") or {})
    if nome == "comparar_por_categoria":
        return metricas.comparar_por_categoria(entrada.get("metrica"), entrada.get("categoria"), entrada.get("filtros") or {})
    if nome == "clientes_em_risco":
        return metricas.clientes_em_risco(entrada.get("nivel", "Alto"))
    if nome == "buscar_registro_cliente":
        return registro_cliente.buscar_registro_cliente(entrada.get("cliente_id"), entrada.get("campo"))
    return {"erro": f"Tool desconhecida: {nome}"}
