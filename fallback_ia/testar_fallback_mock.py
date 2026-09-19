"""
Testa o fluxo de tool use (responder_com_fallback_ia) com a chamada à API
da Groq mockada — valida roteamento, execução da tool contra os dados
reais, o loop multi-turno e os guardrails, sem precisar de rede/chave de
verdade. Serve como substituto do "teste manual" pedido no item 5 do
entregável quando a API real não está acessível.

Os fakes abaixo espelham o formato de resposta da Groq (compatível com
OpenAI): choices[0].message.tool_calls[i].function.{name,arguments}, e
message.model_dump() pra reconstruir o turno anterior nas chamadas
seguintes.

Uso: python -m fallback_ia.testar_fallback_mock
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

from . import ia_fallback
from .metricas import calcular_metrica


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


def caso_consultar_metrica():
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
    # a tool foi executada de verdade contra os dados reais — não é um número inventado
    esperado = calcular_metrica("ticket_medio", {"plano": "Enterprise"})["valor"]
    assert resultado["resultado"]["valor"] == esperado
    print("OK   consultar_metrica (1 turno):", resultado["resposta"])


def caso_buscar_registro_cliente():
    """Pergunta que deveria bater em buscar_registro_cliente, resolvida em 1 turno."""
    tool_call = FakeToolCall("call_2", "buscar_registro_cliente", {"cliente_id": "C007", "campo": "situacao"})
    sequencia = [
        _resposta(FakeMessage(tool_calls=[tool_call])),
        _resposta(FakeMessage(content="O cliente C007 está cancelado desde 03/2026.")),
    ]
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("O cliente C007 ainda está ativo?")

    assert resultado["origem"] == "ia"
    assert resultado["encontrado"] is True
    assert resultado["tool"] == "buscar_registro_cliente"
    assert resultado["resultado"]["situacao"] == "Cancelado"
    print("OK   buscar_registro_cliente (1 turno):", resultado["resposta"])


def caso_multi_turno():
    """
    Reproduz o bug encontrado em teste manual ao vivo: pergunta aberta
    ("diagnóstico geral") faz o modelo chamar uma tool, olhar o resultado,
    e decidir chamar OUTRA tool antes de escrever texto. Um fluxo de 1
    turno trata isso como sucesso com resposta vazia (bug); o loop
    multi-turno precisa continuar até o modelo escrever o texto final.
    """
    tool_call_1 = FakeToolCall("call_3", "consultar_metrica", {"metrica": "ticket_medio", "filtros": {"cliente_id": "C047"}})
    tool_call_2 = FakeToolCall("call_4", "buscar_registro_cliente", {"cliente_id": "C047", "campo": "historico_chamados"})
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
    assert resultado["tool"] == "buscar_registro_cliente"  # última tool chamada
    print("OK   multi-turno (2 tools antes do texto):", resultado["resposta"])


def caso_max_turnos_excedido():
    """Se o modelo só encadear tool_calls sem nunca escrever texto, desiste
    após MAX_TURNOS_TOOL rodadas em vez de girar pra sempre."""
    tool_call = FakeToolCall("call_5", "consultar_metrica", {"metrica": "churn"})
    sequencia = [_resposta(FakeMessage(tool_calls=[tool_call]))] * ia_fallback.MAX_TURNOS_TOOL
    with patch.object(ia_fallback, "_chamar_modelo", side_effect=sequencia):
        resultado = ia_fallback.responder_com_fallback_ia("pergunta que nunca fecha")

    assert resultado == {"origem": "ia", "encontrado": False}
    print("OK   desiste após", ia_fallback.MAX_TURNOS_TOOL, "turnos sem travar")


def caso_fora_do_escopo():
    """Pergunta genuinamente fora do escopo — o modelo não chama nenhuma tool."""
    resposta_sem_tool = _resposta(FakeMessage(content="...", tool_calls=[]))
    with patch.object(ia_fallback, "_chamar_modelo", return_value=resposta_sem_tool):
        resultado = ia_fallback.responder_com_fallback_ia("Qual a previsão do tempo amanhã?")

    assert resultado == {"origem": "ia", "encontrado": False}
    print("OK   fora do escopo -> não encontrado (sem texto livre inventado)")


def caso_timeout():
    """Simula com_timeout estourando o limite — deve cair em 'não encontrei',
    nunca travar o request nem propagar a exceção pro cliente."""
    from .guardrails import FallbackTimeoutError

    with patch.object(ia_fallback, "com_timeout", side_effect=FallbackTimeoutError("excedeu 8s")):
        resultado = ia_fallback.responder_com_fallback_ia("pergunta qualquer")

    assert resultado == {"origem": "ia", "encontrado": False, "erro": "timeout"}
    print("OK   timeout tratado sem travar:", resultado)


if __name__ == "__main__":
    caso_consultar_metrica()
    caso_buscar_registro_cliente()
    caso_multi_turno()
    caso_max_turnos_excedido()
    caso_fora_do_escopo()
    caso_timeout()
    print("\nTodos os cenários (incluindo o multi-turno) passaram (com API mockada).")
