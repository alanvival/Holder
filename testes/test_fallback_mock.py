"""
Testa o fluxo de tool use (responder_com_fallback_ia) com a chamada à API
da Groq mockada — valida roteamento, execução da tool contra os dados
reais, o loop multi-turno e os guardrails, sem precisar de rede/chave de
verdade.

Cobre as 5 tools genéricas (campos.py / tools_genericas.py) que
substituíram a família de tools estreitas (uma por pergunta): os 4 casos
originais do prompt de refatoração (maior cliente, clientes por segmento,
cancelamentos por período, detratores) + os 3 cenários que são o teste real
de que a generalização cobre casos não previstos (comparação indireta,
comparação entre dois períodos, evolução temporal).

Os fakes abaixo espelham o formato de resposta da Groq (compatível com
OpenAI): choices[0].message.tool_calls[i].function.{name,arguments}, e
message.model_dump() pra reconstruir o turno anterior nas chamadas
seguintes.

Uso: pytest testes/test_fallback_mock.py
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from holder.aplicacao.assistente import ia_fallback
from holder.aplicacao.assistente.tools_genericas import listar_clientes, buscar_campo_cliente, comparar_clientes, evolucao_temporal
from holder.dominio.alerta import clientes_em_alerta
from holder.dominio.churn import analisar_fatores_churn
from holder.dominio.metricas import calcular_metrica, comparar_metrica_por_categoria
from holder.dominio.strikes import avaliar_strikes


class FakeFunction:
    def __init__(self, name, arguments_dict):
        self.name = name
        self.arguments = json.dumps(arguments_dict, ensure_ascii=False)


class FakeToolCall:
    def __init__(self, id_, name, arguments_dict):
        self.id = id_
        self.function = FakeFunction(name, arguments_dict)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none=True):
        dados = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            dados["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in self.tool_calls
            ]
        return {k: v for k, v in dados.items() if not exclude_none or v is not None}


def _resposta(mensagem):
    return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


def test_consultar_metrica():
    """Pergunta que deveria bater em consultar_metrica, resolvida em 1 turno."""
    tool_call = FakeToolCall("call_1", "consultar_metrica", {"metrica": "ticket_medio", "filtros": {"plano": "Enterprise"}})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O ticket médio dos clientes Enterprise é R$ 31.111,32, considerando 15 clientes.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual o ticket médio dos clientes Enterprise?")

    assert resultado["origem"] == "ia"
    assert resultado["encontrado"] is True
    assert resultado["tool"] == "consultar_metrica"
    esperado = calcular_metrica("ticket_medio", {"plano": "Enterprise"})["valor"]
    assert resultado["resultado"]["valor"] == esperado
    print("OK   consultar_metrica (1 turno):", resultado["resposta"])


def test_analisar_fatores_churn():
    """Pergunta tipo 'o que mais influencia o cancelamento'."""
    tool_call = FakeToolCall("call_2", "analisar_fatores_churn", {})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="A métrica que mais difere entre clientes ativos e cancelados é chamados críticos (82,6% maior entre quem cancela).")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual métrica mais influencia no cancelamento do cliente?")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "analisar_fatores_churn"
    esperado = analisar_fatores_churn()
    assert resultado["resultado"]["ranking_por_maior_diferenca"] == esperado["ranking_por_maior_diferenca"]
    print("OK   analisar_fatores_churn:", resultado["resposta"])


def test_clientes_em_alerta():
    """Pergunta tipo 'quais clientes estão em risco alto agora'."""
    tool_call = FakeToolCall("call_3", "clientes_em_alerta", {"nivel": "Alto"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="4 clientes estão em risco alto: C019, C029, C067 e C080.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Quais clientes estão em risco alto agora?")

    assert resultado["encontrado"] is True
    esperado_ids = {c["cliente_id"] for c in clientes_em_alerta("Alto")["clientes"]}
    obtido_ids = {c["cliente_id"] for c in resultado["resultado"]["clientes"]}
    assert obtido_ids == esperado_ids
    print("OK   clientes_em_alerta:", resultado["resposta"])


def test_clientes_com_strikes():
    """Pergunta tipo 'faça uma predição de cancelamento' — diferente de
    clientes_em_alerta (diagnóstico contra a própria história), compara o
    cliente ativo com o padrão real de quem já cancelou."""
    tool_call = FakeToolCall("call_21", "clientes_com_strikes", {"cliente_id": "C067"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O cliente C067 bateu 4 de 4 sinais de alerta: SLA crítico, lentidão, reclamação recente e NPS detrator — mesmo padrão de quem já cancelou.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Faça uma predição de cancelamento pro cliente C067")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "clientes_com_strikes"
    esperado = avaliar_strikes("C067")
    assert resultado["resultado"]["total_strikes"] == esperado["total_strikes"]
    assert resultado["resultado"]["strikes"] == esperado["strikes"]
    print("OK   clientes_com_strikes (semelhança, não diagnóstico):", resultado["resposta"])


@pytest.mark.sqlserver
def test_listar_previsao_risco():
    """Pergunta tipo 'quais empresas podem dar problema' — modelo
    estatístico (regressão logística) via SQL Server, não a heurística de
    strikes. Skippa graciosamente se o SQL Server não estiver acessível
    nesta máquina (ambiente de CI, por exemplo)."""
    from holder.aplicacao.assistente import previsao_risco
    esperado = previsao_risco.listar_previsao_risco({"faixa": "Crítico"}, 5)
    if "erro" in esperado:
        pytest.skip(f"SQL Server indisponível: {esperado['erro']}")

    tool_call = FakeToolCall("call_22", "listar_previsao_risco", {"faixa": "Crítico", "limite": 5})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="Os clientes em risco crítico de cancelamento são: " + ", ".join(c["cliente_id"] for c in esperado["clientes"]))),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Quais empresas podem dar problema (risco crítico)?")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "listar_previsao_risco"
    assert resultado["resultado"]["clientes"] == esperado["clientes"]
    print("OK   listar_previsao_risco (modelo estatístico real):", resultado["resposta"])


@pytest.mark.sqlserver
def test_detalhar_previsao_cliente():
    """Pergunta tipo 'por que o cliente X tem esse risco' — explicabilidade
    do modelo (coeficiente × desvio por sinal) + trajetória histórica."""
    from holder.aplicacao.assistente import previsao_risco
    esperado = previsao_risco.detalhar_previsao_cliente("C071")
    if "erro" in esperado:
        pytest.skip(f"SQL Server indisponível: {esperado['erro']}")

    tool_call = FakeToolCall("call_23", "detalhar_previsao_cliente", {"cliente_id": "C071"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content=f"O cliente C071 tem {esperado['risco_percentual']}% de risco previsto, faixa {esperado['faixa']}.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Por que o cliente C071 tem esse risco de cancelamento?")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "detalhar_previsao_cliente"
    assert resultado["resultado"]["risco_percentual"] == esperado["risco_percentual"]
    assert resultado["resultado"]["sinais_detalhados"] == esperado["sinais_detalhados"]
    print("OK   detalhar_previsao_cliente (explicabilidade + trajetória):", resultado["resposta"])


@pytest.mark.sqlserver
def test_historico_resolve_referencia():
    """Reproduz o bug reportado ao vivo: sem histórico de conversa, 'esse
    cliente' não tem a quem se referir — a pergunta sozinha nunca chegaria
    em detalhar_previsao_cliente(C071) sem o contexto do turno anterior.
    Confere que o histórico enviado pelo front (useAssistant.js) é
    injetado nas mensagens ANTES da pergunta nova."""
    from holder.aplicacao.assistente import previsao_risco
    esperado = previsao_risco.detalhar_previsao_cliente("C071")
    if "erro" in esperado:
        pytest.skip(f"SQL Server indisponível: {esperado['erro']}")

    historico = [
        {"role": "user", "content": "Qual o risco de cancelamento do cliente C071?"},
        {"role": "assistant", "content": f"O cliente C071 tem {esperado['risco_percentual']}% de risco, faixa {esperado['faixa']}."},
    ]
    tool_call = FakeToolCall("call_24", "detalhar_previsao_cliente", {"cliente_id": "C071"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O principal motivo é o NPS detrator e a lentidão de resolução.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia) as mock_chamar:
        resultado = ia_fallback.responder_com_fallback_ia("Por que esse cliente tem esse risco de cancelar?", historico=historico)

    # As mensagens mandadas pro modelo no 1º turno precisam conter o
    # histórico entre o system prompt e a pergunta nova.
    primeira_chamada_mensagens = mock_chamar.call_args_list[0].args[0]
    assert primeira_chamada_mensagens[1] == historico[0]
    assert primeira_chamada_mensagens[2] == historico[1]
    assert primeira_chamada_mensagens[3]["content"] == "Por que esse cliente tem esse risco de cancelar?"

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "detalhar_previsao_cliente"
    assert resultado["resultado"]["cliente_id"] == "C071"
    print("OK   histórico de conversa resolve 'esse cliente' pro C071 certo:", resultado["resposta"])


def test_metrica_agrupada_por_categoria():
    """Reproduz o bug reportado ao vivo: 'ticket médio por segmento'
    estourava MAX_TURNOS_TOOL porque o modelo tentava listar segmentos +
    chamar consultar_metrica uma vez por valor (6 chamadas, mais que o
    orçamento). consultar_metrica com agrupar_por resolve numa chamada só."""
    tool_call = FakeToolCall("call_20", "consultar_metrica", {"metrica": "ticket_medio", "agrupar_por": "segmento"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="Ticket médio por segmento: Varejo R$ 17.488,50, Serviços R$ 16.266,08...")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual o ticket médio por segmento?")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "consultar_metrica"
    esperado = comparar_metrica_por_categoria("ticket_medio", "segmento")
    assert resultado["resultado"]["comparacao"] == esperado["comparacao"]
    print("OK   métrica agrupada por categoria (1 chamada, sem estourar turnos):", resultado["resposta"])


# --- Os 4 casos originais do prompt de refatoração (via listar_clientes) --

def test_maior_cliente():
    """'Qual o maior cliente' -> listar_clientes com ordenar_por='valor_mensal',
    direcao='desc', limite=1 — ranking vira um caso particular de listagem."""
    tool_call = FakeToolCall(
        "call_4", "listar_clientes",
        {"ordenar_por": "valor_mensal", "direcao": "desc", "limite": 1},
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O maior cliente é o C032, com valor mensal de R$ 36.208,00.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual é o maior cliente?")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "listar_clientes"
    esperado = listar_clientes(ordenar_por="valor_mensal", direcao="desc", limite=1)
    assert resultado["resultado"]["clientes"] == esperado["clientes"] == ["C032"]
    print("OK   maior cliente (listar_clientes + ordenar_por):", resultado["resposta"])


def test_clientes_por_segmento():
    """'Quais clientes são do segmento Varejo' -> listar_clientes com filtro simples."""
    tool_call = FakeToolCall(
        "call_5", "listar_clientes",
        {"filtros": [{"campo": "segmento", "operador": "igual", "valor": "Varejo"}]},
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="16 clientes são do segmento Varejo: C010, C011, C015...")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Quais clientes são do segmento Varejo?")

    assert resultado["encontrado"] is True
    esperado = listar_clientes(filtros=[{"campo": "segmento", "operador": "igual", "valor": "Varejo"}])
    assert resultado["resultado"]["total_encontrado"] == esperado["total_encontrado"] == 16
    print("OK   clientes por segmento (listar_clientes):", resultado["resposta"])


def test_cancelamentos_por_periodo():
    """'Quantos clientes cancelaram em 2026' -> listar_clientes com
    retornar='contagem', filtrando mes_cancelamento por 'entre'."""
    tool_call = FakeToolCall(
        "call_6", "listar_clientes",
        {
            "filtros": [{"campo": "mes_cancelamento", "operador": "entre", "valor": "2026-01", "valor2": "2026-12"}],
            "retornar": "contagem",
        },
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="12 clientes cancelaram em 2026.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Quantos clientes cancelaram em 2026?")

    assert resultado["encontrado"] is True
    esperado = listar_clientes(
        filtros=[{"campo": "mes_cancelamento", "operador": "entre", "valor": "2026-01", "valor2": "2026-12"}],
        retornar="contagem",
    )
    assert resultado["resultado"]["total"] == esperado["total"] == 12
    print("OK   cancelamentos por período (listar_clientes, retornar=contagem):", resultado["resposta"])


def test_detratores():
    """'Quais clientes são detratores' -> listar_clientes filtrando
    classificacao_nps (campo de série temporal — usa a pesquisa mais recente)."""
    tool_call = FakeToolCall(
        "call_7", "listar_clientes",
        {"filtros": [{"campo": "classificacao_nps", "operador": "igual", "valor": "Detrator"}], "limite": 100},
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="33 clientes são detratores.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Quais clientes são detratores?")

    assert resultado["encontrado"] is True
    esperado = listar_clientes(filtros=[{"campo": "classificacao_nps", "operador": "igual", "valor": "Detrator"}], limite=100)
    assert resultado["resultado"]["total_encontrado"] == esperado["total_encontrado"] == 33
    print("OK   detratores (listar_clientes, campo de série temporal):", resultado["resposta"])


# --- buscar_campo_cliente (cobre a lacuna real: "qual dia entrou o cliente") -

def test_buscar_campo_cliente():
    tool_call = FakeToolCall("call_8", "buscar_campo_cliente", {"cliente_id": "C002", "campos": ["inicio_contrato", "plano"]})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O cliente C002 iniciou o contrato em 01/02/2020, no plano Avançado.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual dia entrou o cliente C002?")

    assert resultado["encontrado"] is True
    assert resultado["resultado"]["inicio_contrato"] == "2020-02-01"
    print("OK   buscar_campo_cliente:", resultado["resposta"])


def test_normaliza_cliente_id_com_erro_de_digitacao():
    """Reproduz o bug reportado ao vivo: 'CO02' (letra O) em vez de 'C002'
    (zero) — a tool tem que normalizar antes de buscar."""
    tool_call = FakeToolCall("call_9", "buscar_campo_cliente", {"cliente_id": "CO02", "campos": ["inicio_contrato"]})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O cliente C002 iniciou o contrato em 01/02/2020.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual dia entrou o cliente CO02?")

    assert resultado["encontrado"] is True
    assert resultado["resultado"]["cliente_id"] == "C002"
    assert resultado["resultado"]["inicio_contrato"] == "2020-02-01"
    print("OK   normaliza cliente_id com erro de digitação (CO02 -> C002):", resultado["resposta"])


# --- Os 3 cenários novos (teste real de generalização) ---------------------

def test_comparacao_indireta():
    """'Compare o maior cliente do Varejo com o de Saúde' — o modelo não
    conhece os cliente_id de antemão: precisa encadear duas chamadas de
    listar_clientes (uma por segmento) pra descobrir quem são, e só então
    chamar comparar_clientes. É o teste do encadeamento de tools do system
    prompt (Passo 3), não só de uma tool isolada."""
    tool_call_varejo = FakeToolCall(
        "call_10", "listar_clientes",
        {"filtros": [{"campo": "segmento", "operador": "igual", "valor": "Varejo"}], "ordenar_por": "valor_mensal", "direcao": "desc", "limite": 1},
    )
    tool_call_saude = FakeToolCall(
        "call_11", "listar_clientes",
        {"filtros": [{"campo": "segmento", "operador": "igual", "valor": "Saude"}], "ordenar_por": "valor_mensal", "direcao": "desc", "limite": 1},
    )
    maior_varejo = listar_clientes(filtros=[{"campo": "segmento", "operador": "igual", "valor": "Varejo"}], ordenar_por="valor_mensal", direcao="desc", limite=1)["clientes"][0]
    maior_saude = listar_clientes(filtros=[{"campo": "segmento", "operador": "igual", "valor": "Saude"}], ordenar_por="valor_mensal", direcao="desc", limite=1)["clientes"][0]
    tool_call_comparar = FakeToolCall(
        "call_12", "comparar_clientes",
        {"cliente_ids": [maior_varejo, maior_saude], "campos": ["valor_mensal", "plano"]},
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call_varejo])),
        _resposta(FakeMessage(tool_calls=[tool_call_saude])),
        _resposta(FakeMessage(tool_calls=[tool_call_comparar])),
        _resposta(FakeMessage(content=f"O maior cliente do Varejo ({maior_varejo}) tem valor mensal maior/menor que o maior de Saúde ({maior_saude}).")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Compare o maior cliente do Varejo com o de Saúde")

    assert resultado["encontrado"] is True
    assert resultado["tool"] == "comparar_clientes"
    ids_comparados = {c["cliente_id"] for c in resultado["resultado"]["clientes"]}
    assert ids_comparados == {maior_varejo, maior_saude}
    print("OK   comparação indireta (encadeamento de 3 tools):", resultado["resposta"])


def test_comparacao_entre_periodos():
    """'Compare o cliente C047 entre 2025 e 2026' — mesmo cliente, dois
    períodos, via periodo_comparacao."""
    tool_call = FakeToolCall(
        "call_13", "comparar_clientes",
        {
            "cliente_ids": ["C047"], "campos": ["pct_sla_cumprido"],
            "periodo_inicio": "2025-01", "periodo_fim": "2025-12",
            "periodo_comparacao": {"periodo_inicio": "2026-01", "periodo_fim": "2026-12"},
        },
    )
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O SLA cumprido do cliente C047 mudou entre 2025 e 2026.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Compare o SLA do cliente C047 entre 2025 e 2026")

    assert resultado["encontrado"] is True
    assert resultado["resultado"]["modo"] == "entre_periodos"
    esperado = comparar_clientes(
        ["C047"], ["pct_sla_cumprido"], "2025-01", "2025-12",
        {"periodo_inicio": "2026-01", "periodo_fim": "2026-12"},
    )
    assert resultado["resultado"]["clientes"] == esperado["clientes"]
    print("OK   comparação entre dois períodos (mesmo cliente):", resultado["resposta"])


def test_evolucao_temporal():
    """'Como evoluiu o uso da plataforma do cliente C047 nos últimos meses' —
    nenhuma tool anterior devolvia série mensal de um campo bruto."""
    tool_call = FakeToolCall("call_14", "evolucao_temporal", {"campo": "uso_plataforma_pct", "cliente_id": "C047"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O uso da plataforma do cliente C047 variou mês a mês assim: ...")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Como evoluiu o uso da plataforma do cliente C047?")

    assert resultado["encontrado"] is True
    esperado = evolucao_temporal("uso_plataforma_pct", cliente_id="C047")
    assert resultado["resultado"]["tabela"] == esperado["tabela"]
    assert len(resultado["resultado"]["tabela"]["linhas"]) > 0
    print("OK   evolução temporal (cliente único):", resultado["resposta"])


def test_campo_invalido():
    """Campo fora do allowlist -> erro estruturado com sugestão, nunca
    exceção crua nem acesso a coluna arbitrária."""
    tool_call = FakeToolCall("call_15", "buscar_campo_cliente", {"cliente_id": "C001", "campos": ["nome_fantasia"]})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="Esse campo não existe na base.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Qual o nome fantasia do cliente C001?")

    assert resultado["encontrado"] is True
    assert "erro" in resultado["resultado"]
    assert "campos_validos" in resultado["resultado"]
    print("OK   campo inválido -> erro estruturado com sugestão:", resultado["resultado"]["erro"])


def test_multi_turno():
    """
    Reproduz o bug encontrado em teste manual ao vivo: pergunta aberta
    ("diagnóstico geral") faz o modelo chamar uma tool, olhar o resultado,
    e decidir chamar OUTRA tool antes de escrever texto.
    """
    tool_call_1 = FakeToolCall("call_16", "consultar_metrica", {"metrica": "ticket_medio", "filtros": {"cliente_id": "C047"}})
    tool_call_2 = FakeToolCall("call_17", "buscar_campo_cliente", {"cliente_id": "C047", "campos": ["chamados_criticos"]})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call_1])),
        _resposta(FakeMessage(tool_calls=[tool_call_2])),  # 2ª tool em vez de texto — o caso que quebrava
        _resposta(FakeMessage(content="Diagnóstico do cliente C047: ticket médio R$ 33.196,00, sem chamados críticos recentes.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("Me dê um diagnóstico geral do cliente C047")

    assert resultado["origem"] == "ia"
    assert resultado["encontrado"] is True
    assert resultado["resposta"]  # não pode vir vazio
    assert resultado["tool"] == "buscar_campo_cliente"  # última tool chamada
    print("OK   multi-turno (2 tools antes do texto):", resultado["resposta"])


def test_max_turnos_excedido():
    """Se o modelo só encadear tool_calls sem nunca escrever texto, desiste
    após MAX_TURNOS_TOOL rodadas em vez de girar pra sempre."""
    tool_call = FakeToolCall("call_18", "consultar_metrica", {"metrica": "churn"})
    sequencia = [_resposta(FakeMessage(tool_calls=[tool_call]))] * ia_fallback.MAX_TURNOS_TOOL
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("pergunta que nunca fecha")

    assert resultado == {"origem": "ia", "encontrado": False}
    print("OK   desiste após", ia_fallback.MAX_TURNOS_TOOL, "turnos sem travar")


def test_fora_do_escopo():
    """Pergunta genuinamente fora do escopo — o modelo não chama nenhuma tool."""
    resposta_sem_tool = _resposta(FakeMessage(content="...", tool_calls=[]))
    with patch.object(ia_fallback, "_chamar_modelo", return_value=resposta_sem_tool):
        resultado = ia_fallback.responder_com_fallback_ia("Qual a previsão do tempo amanhã?")

    assert resultado == {"origem": "ia", "encontrado": False}
    print("OK   fora do escopo -> não encontrado (sem texto livre inventado)")


def test_timeout():
    """Simula com_timeout estourando o limite — deve cair em 'não encontrei',
    nunca travar o request nem propagar a exceção pro cliente."""
    from holder.infra.ia.guardrails import FallbackTimeoutError

    with patch.object(ia_fallback, "com_timeout", side_effect=FallbackTimeoutError("excedeu 20s")):
        resultado = ia_fallback.responder_com_fallback_ia("pergunta qualquer")

    assert resultado == {"origem": "ia", "encontrado": False, "erro": "timeout"}
    print("OK   timeout tratado sem travar:", resultado)


