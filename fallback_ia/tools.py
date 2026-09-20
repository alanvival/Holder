"""
Schema das tools expostas ao provedor de IA (formato Anthropic —
`input_schema` — que é a fonte da verdade). `tools_formato_openai()`
converte pro formato usado pela Groq/OpenAI (`function.parameters`), sem
duplicar o schema — um só lugar descreve as tools, cada provedor só lê num
formato diferente.

Refatorado pra tools GENÉRICAS (ver fallback_ia/campos.py e
fallback_ia/tools_genericas.py): antes, cada pergunta nova exigia uma tool
nova e estreita (ranking_clientes, contar_clientes, evolucao_metrica,
comparar_por_categoria, listar_clientes antigo, buscar_registro_cliente) —
isso não escala, o número de perguntas possíveis é infinito. Agora
`listar_clientes`, `buscar_campo_cliente`, `comparar_clientes` e
`evolucao_temporal` cobrem essas famílias inteiras via parâmetros (campo é
validado contra CAMPOS_PERMITIDOS, nunca vira nome de coluna cru).
`consultar_metrica` continua à parte porque métricas agregadas (ticket
médio, SLA, NPS, churn...) são CÁLCULOS com fórmula própria, não um campo
só; `analisar_fatores_churn` e `clientes_em_risco` também continuam à parte
pelo mesmo motivo — são análises que cruzam várias métricas, não uma leitura
de campo.
"""
from __future__ import annotations

from . import tools_genericas, previsao_risco
from holder.infra.dados import carteira as dados
from holder.dominio.alerta import clientes_em_risco
from holder.dominio.churn import analisar_fatores_churn
from holder.dominio.metricas import calcular_metrica, comparar_metrica_por_categoria
from holder.dominio.strikes import prever_risco_cancelamento

TOOLS = [
    {
        "name": "consultar_metrica",
        "description": (
            "Calcula uma métrica agregada sobre a base de clientes "
            "(ticket médio, antiguidade de contrato, SLA contratado, tempo "
            "de resolução, reclamações, atraso de pagamento, SLA cumprido, "
            "NPS, churn, uso da plataforma, reuniões, chamados críticos, "
            "taxa de reabertura), com filtros opcionais. Use 'agrupar_por' "
            "pra perguntas tipo 'ticket médio POR segmento' ou 'compare o "
            "SLA entre os planos' — calcula a métrica pra cada valor da "
            "categoria numa chamada só, em vez de uma chamada por valor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrica": {
                    "type": "string",
                    "enum": [
                        "ticket_medio", "antiguidade_contrato", "sla_contratado",
                        "tempo_medio_resolucao", "media_reclamacoes", "atraso_pagamento",
                        "sla_cumprido", "nps", "churn", "uso_plataforma",
                        "reunioes_realizadas", "chamados_criticos", "taxa_reabertura",
                    ],
                    "description": "Qual métrica calcular. 'antiguidade_contrato' = dias desde o início do contrato.",
                },
                "agrupar_por": {
                    "type": "string",
                    "enum": ["plano", "porte", "segmento"],
                    "description": "Opcional — quando presente, devolve a métrica comparada entre todos os valores dessa categoria, não um número só.",
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
            "cancelados e devolve um ranking de qual métrica mais difere "
            "entre os dois grupos. Use pra perguntas tipo 'o que mais "
            "influencia o cancelamento', 'quais fatores levam ao churn'. "
            "Não tem parâmetros — sempre compara a carteira inteira."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "clientes_em_risco",
        "description": (
            "Lista clientes ativos classificados num nível de risco de "
            "cancelamento (Alto, Médio ou Baixo) por uma pontuação "
            "ponderada estilo credit score (soma de pesos dos sinais que "
            "dispararam, calibrados pelo quanto cada sinal realmente "
            "diferencia clientes ativos de cancelados na base — não uma "
            "contagem simples), comparando o mês mais recente de cada "
            "cliente com a própria média histórica DELE MESMO. É "
            "diagnóstico (piorou em relação a si próprio?), não predição — "
            "pra predição (o cliente se parece com quem já cancelou?) use "
            "prever_risco_cancelamento. Use clientes_em_risco pra "
            "perguntas tipo 'quais clientes estão em risco', 'quem eu "
            "devo ligar primeiro'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nivel": {"type": "string", "enum": ["Alto", "Médio", "Baixo"], "description": "Padrão: Alto."},
            },
        },
    },
    {
        "name": "prever_risco_cancelamento",
        "description": (
            "PREDIÇÃO heurística (versão de reserva — prefira "
            "listar_previsao_risco/detalhar_previsao_cliente quando a "
            "pergunta for sobre probabilidade/porcentagem de risco; use "
            "esta só se aquelas devolverem erro, ex: banco indisponível). "
            "Compara o(s) cliente(s) ativo(s) com o padrão real de "
            "comportamento de clientes que JÁ cancelaram nos últimos "
            "meses antes de sair (SLA crítico, lentidão, reclamação "
            "recente, NPS detrator) — cada sinal batido é um 'strike', "
            "sem uma probabilidade calibrada por trás."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "Opcional — avalia só esse cliente. Sem isso, lista todos os ativos com pelo menos 1 alerta."},
                "limite": {"type": "integer", "description": "Máximo de clientes a listar quando sem cliente_id (padrão 20, máximo 100)."},
            },
        },
    },
    {
        "name": "listar_previsao_risco",
        "description": (
            "PREDIÇÃO estatística de cancelamento — probabilidade real "
            "(0-100%) por cliente, vinda de um modelo de regressão "
            "logística TREINADO e VALIDADO contra os cancelamentos reais "
            "da base (validação cruzada 5-fold: AUC~0.95, Brier~0.085 — "
            "não é uma nota heurística). Devolve a lista ranqueada de "
            "clientes por risco, com a faixa (Saudável/Atenção/Em risco/"
            "Crítico) e a tendência (subindo/caindo/estável desde o mês "
            "anterior). Use pra perguntas tipo 'quais empresas podem dar "
            "problema', 'qual a probabilidade de cancelamento de cada "
            "cliente', 'quais clientes estão em risco crítico agora', "
            "'me dá o relatório preditivo', 'quais intervenções devo "
            "priorizar'. Fonte: SQL Server (fScoreRisco, atualizado "
            "mensalmente pelo job de treino) — se devolver erro, o banco "
            "pode estar fora do ar; nesse caso use prever_risco_cancelamento."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "faixa": {"type": "string", "enum": ["Crítico", "Em risco", "Atenção", "Saudável"], "description": "Opcional — filtra só uma faixa de risco."},
                "limite": {"type": "integer", "description": "Máximo de clientes a listar (padrão 20, máximo 100)."},
            },
        },
    },
    {
        "name": "detalhar_previsao_cliente",
        "description": (
            "Detalhe da PREDIÇÃO estatística (mesmo modelo de "
            "listar_previsao_risco) pra UM cliente específico: "
            "probabilidade atual, explicabilidade (quais variáveis mais "
            "contribuem pro risco desse cliente — SLA, uso da plataforma, "
            "atraso de pagamento, chamados críticos, reclamações, tempo "
            "de resolução, NPS) e a trajetória do risco nos últimos "
            "meses (pra ver se está piorando/melhorando ao longo do "
            "tempo, não só o número de agora). Use pra perguntas tipo "
            "'por que o cliente X tem esse risco', 'qual a evolução do "
            "risco do cliente X', 'o que está pesando mais no risco "
            "desse cliente'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "ID do cliente, ex: C071"},
            },
            "required": ["cliente_id"],
        },
    },
    {
        "name": "listar_clientes",
        "description": (
            "Tool genérica de busca/ranking/contagem/agrupamento de "
            "clientes — cobre qualquer combinação de filtros sobre qualquer "
            "campo do allowlist (segmento, porte, plano, situação, valor "
            "mensal, SLA contratado, início de contrato, mês de "
            "cancelamento, chamados, SLA cumprido, reclamações, uso da "
            "plataforma, atraso de pagamento, reuniões, NPS...). "
            "'retornar' decide o formato: 'lista' = os cliente_id que "
            "batem (com 'ordenar_por' vira ranking, ex: 'qual o maior "
            "cliente' -> ordenar_por='valor_mensal', direcao='desc', "
            "limite=1); 'contagem' = só o total (ex: 'quantos clientes "
            "cancelaram'); 'agrupado' = contagem por valor de um campo "
            "(ex: 'cancelamentos por segmento' -> agrupar_por='segmento', "
            "com filtros=[{campo:'situacao',operador:'igual',valor:"
            "'Cancelado'}])."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filtros": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "campo": {"type": "string", "description": "Campo do allowlist — ver buscar_campo_cliente pra lista completa."},
                            "operador": {"type": "string", "enum": ["igual", "diferente", "maior_que", "menor_que", "contem", "entre"]},
                            "valor": {"type": ["string", "number"]},
                            "valor2": {"type": ["string", "number"], "description": "Usado só com operador 'entre'."},
                        },
                        "required": ["campo", "operador", "valor"],
                    },
                },
                "ordenar_por": {"type": "string", "description": "Campo do allowlist pra ordenar/ranquear."},
                "direcao": {"type": "string", "enum": ["asc", "desc"], "description": "Padrão desc (maior primeiro)."},
                "periodo_inicio": {"type": "string", "description": "AAAA-MM — aplica-se a campos de série temporal usados em filtros/ordenar_por."},
                "periodo_fim": {"type": "string"},
                "limite": {"type": "integer", "description": "Padrão 20, máximo 100. Ignorado quando retornar='contagem'."},
                "retornar": {"type": "string", "enum": ["lista", "contagem", "agrupado"], "description": "Padrão 'lista'."},
                "agrupar_por": {"type": "string", "description": "Campo do allowlist — obrigatório quando retornar='agrupado'."},
            },
        },
    },
    {
        "name": "buscar_campo_cliente",
        "description": (
            "Busca um ou mais campos pontuais de UM cliente específico — "
            "cobre qualquer campo do allowlist: segmento, porte, plano, "
            "valor_mensal, sla_contratado_h, inicio_contrato (data que o "
            "contrato começou), situacao, mes_cancelamento, chamados_*, "
            "pct_sla_cumprido, tempo_medio_resolucao_h, "
            "reclamacoes_formais, uso_plataforma_pct, "
            "dias_atraso_pagamento, reunioes_realizadas/previstas, "
            "nota_nps, classificacao_nps. Campo de série temporal sem "
            "período pega o mês mais recente disponível."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {"type": "string", "description": "ID do cliente, ex: C007"},
                "campos": {"type": "array", "items": {"type": "string"}},
                "periodo_inicio": {"type": "string", "description": "AAAA-MM"},
                "periodo_fim": {"type": "string", "description": "AAAA-MM — se omitido, usa o mês mais recente disponível."},
            },
            "required": ["cliente_id", "campos"],
        },
    },
    {
        "name": "comparar_clientes",
        "description": (
            "Compara dois ou mais clientes num mesmo período, OU compara "
            "o(s) mesmo(s) cliente(s) entre dois períodos diferentes (ex: "
            "2025 vs 2026, informando 'periodo_comparacao'). Pra comparar "
            "clientes descritos indiretamente (\"o maior cliente do Varejo "
            "com o de Saúde\"), primeiro use listar_clientes pra descobrir "
            "os cliente_id, e só então chame esta tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "campos": {"type": "array", "items": {"type": "string"}},
                "periodo_inicio": {"type": "string"},
                "periodo_fim": {"type": "string"},
                "periodo_comparacao": {
                    "type": "object",
                    "description": "Segundo intervalo de período pra comparar contra o principal — presente só quando a pergunta compara dois períodos, não dois clientes.",
                    "properties": {
                        "periodo_inicio": {"type": "string"},
                        "periodo_fim": {"type": "string"},
                    },
                },
            },
            "required": ["cliente_ids", "campos"],
        },
    },
    {
        "name": "evolucao_temporal",
        "description": (
            "Retorna a evolução mês a mês (ou pesquisa a pesquisa, para "
            "campos de NPS) de UM campo de série temporal — pra um cliente "
            "específico (cliente_id) ou agregado sobre um grupo de "
            "clientes (filtros, mesmo formato de listar_clientes). Use pra "
            "perguntas tipo 'como o SLA evoluiu', 'a carteira está "
            "melhorando ou piorando'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "campo": {"type": "string", "description": "Campo de série temporal do allowlist (ex: pct_sla_cumprido, uso_plataforma_pct, chamados_criticos, nota_nps, classificacao_nps)."},
                "cliente_id": {"type": "string", "description": "Opcional — se omitido, agrega sobre 'filtros'."},
                "filtros": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "campo": {"type": "string"},
                            "operador": {"type": "string", "enum": ["igual", "diferente", "maior_que", "menor_que", "contem", "entre"]},
                            "valor": {"type": ["string", "number"]},
                            "valor2": {"type": ["string", "number"]},
                        },
                        "required": ["campo", "operador", "valor"],
                    },
                    "description": "Usado só quando cliente_id é omitido, pra agregar um grupo (ex: média do segmento Varejo).",
                },
                "periodo_inicio": {"type": "string"},
                "periodo_fim": {"type": "string"},
            },
            "required": ["campo"],
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


def _normalizar_entrada(entrada: dict) -> dict:
    """Corrige erros de digitação comuns no cliente_id (ex: 'CO02' -> 'C002')
    antes de rodar qualquer tool — no parâmetro direto, dentro de filtros
    aninhados (dict, tool antiga consultar_metrica) e dentro de listas de
    filtro (array, tools genéricas) e de cliente_ids."""
    entrada = dict(entrada or {})
    if "cliente_id" in entrada:
        entrada["cliente_id"] = dados.normalizar_cliente_id(entrada["cliente_id"])
    if isinstance(entrada.get("cliente_ids"), list):
        entrada["cliente_ids"] = [dados.normalizar_cliente_id(c) for c in entrada["cliente_ids"]]

    filtros = entrada.get("filtros")
    if isinstance(filtros, dict) and "cliente_id" in filtros:
        filtros = dict(filtros)
        filtros["cliente_id"] = dados.normalizar_cliente_id(filtros["cliente_id"])
        entrada["filtros"] = filtros
    elif isinstance(filtros, list):
        nova_lista = []
        for f in filtros:
            if isinstance(f, dict) and f.get("campo") == "cliente_id":
                f = dict(f)
                f["valor"] = dados.normalizar_cliente_id(f.get("valor"))
            nova_lista.append(f)
        entrada["filtros"] = nova_lista
    return entrada


def executar_tool(nome: str, entrada: dict) -> dict:
    """Roda a consulta de verdade contra os dados reais. Nunca retorna texto
    livre — sempre um dict estruturado que a Claude só pode reformatar."""
    entrada = _normalizar_entrada(entrada)
    if nome == "consultar_metrica":
        if entrada.get("agrupar_por"):
            return comparar_metrica_por_categoria(
                entrada.get("metrica"), entrada.get("agrupar_por"), entrada.get("filtros") or {},
            )
        return calcular_metrica(entrada.get("metrica"), entrada.get("filtros") or {})
    if nome == "analisar_fatores_churn":
        return analisar_fatores_churn()
    if nome == "clientes_em_risco":
        return clientes_em_risco(entrada.get("nivel", "Alto"))
    if nome == "prever_risco_cancelamento":
        return prever_risco_cancelamento(entrada.get("cliente_id"), entrada.get("limite", 20))
    if nome == "listar_previsao_risco":
        return previsao_risco.listar_previsao_risco({"faixa": entrada.get("faixa")} if entrada.get("faixa") else {}, entrada.get("limite", 20))
    if nome == "detalhar_previsao_cliente":
        return previsao_risco.detalhar_previsao_cliente(entrada.get("cliente_id"))
    if nome == "listar_clientes":
        return tools_genericas.listar_clientes(
            filtros=entrada.get("filtros"),
            ordenar_por=entrada.get("ordenar_por"),
            direcao=entrada.get("direcao", "desc"),
            periodo_inicio=entrada.get("periodo_inicio"),
            periodo_fim=entrada.get("periodo_fim"),
            limite=entrada.get("limite", 20),
            retornar=entrada.get("retornar", "lista"),
            agrupar_por=entrada.get("agrupar_por"),
        )
    if nome == "buscar_campo_cliente":
        return tools_genericas.buscar_campo_cliente(
            entrada.get("cliente_id"), entrada.get("campos") or [],
            entrada.get("periodo_inicio"), entrada.get("periodo_fim"),
        )
    if nome == "comparar_clientes":
        return tools_genericas.comparar_clientes(
            entrada.get("cliente_ids") or [], entrada.get("campos") or [],
            entrada.get("periodo_inicio"), entrada.get("periodo_fim"),
            entrada.get("periodo_comparacao"),
        )
    if nome == "evolucao_temporal":
        return tools_genericas.evolucao_temporal(
            entrada.get("campo"), entrada.get("cliente_id"), entrada.get("filtros"),
            entrada.get("periodo_inicio"), entrada.get("periodo_fim"),
        )
    return {"erro": f"Tool desconhecida: {nome}"}
