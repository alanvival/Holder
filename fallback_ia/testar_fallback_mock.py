"""
Testa o fluxo de tool use (responder_com_fallback_ia) com a chamada à Claude
API mockada — valida roteamento, execução da tool contra os dados reais e
os guardrails, sem precisar de uma ANTHROPIC_API_KEY de verdade. Serve como
substituto do "teste manual" pedido no item 5 do entregável até alguém
rodar com a chave real (server.py + curl / o widget de verdade).

Uso: python -m fallback_ia.testar_fallback_mock
"""
from types import SimpleNamespace
from unittest.mock import patch

from . import claude_fallback
from .metricas import calcular_metrica


def _bloco_tool(nome, entrada, id_="toolu_1"):
    return SimpleNamespace(type="tool_use", name=nome, input=entrada, id=id_)


def _bloco_texto(texto):
    return SimpleNamespace(type="text", text=texto)


def caso_consultar_metrica():
    """Pergunta que deveria bater em consultar_metrica."""
    resposta_tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[_bloco_tool("consultar_metrica", {"metrica": "ticket_medio", "filtros": {"plano": "Enterprise"}})],
    )
    resposta_final = SimpleNamespace(
        content=[_bloco_texto("O ticket médio dos clientes Enterprise é R$ 31.111,32, considerando 15 clientes.")],
    )
    with patch.object(claude_fallback, "_chamar_claude", return_value=resposta_tool_use), \
         patch.object(claude_fallback, "_chamar_claude_com_resultado", return_value=resposta_final):
        resultado = claude_fallback.responder_com_fallback_ia("Qual o ticket médio dos clientes Enterprise?")

    assert resultado["origem"] == "ia"
    assert resultado["encontrado"] is True
    assert resultado["tool"] == "consultar_metrica"
    # a tool foi executada de verdade contra os dados reais — não é um número inventado
    esperado = calcular_metrica("ticket_medio", {"plano": "Enterprise"})["valor"]
    assert resultado["resultado"]["valor"] == esperado
    print("OK   consultar_metrica:", resultado["resposta"])


def caso_buscar_registro_cliente():
    """Pergunta que deveria bater em buscar_registro_cliente."""
    resposta_tool_use = SimpleNamespace(
        stop_reason="tool_use",
        content=[_bloco_tool("buscar_registro_cliente", {"cliente_id": "C007", "campo": "situacao"})],
    )
    resposta_final = SimpleNamespace(
        content=[_bloco_texto("O cliente C007 está cancelado desde 03/2026.")],
    )
    with patch.object(claude_fallback, "_chamar_claude", return_value=resposta_tool_use), \
         patch.object(claude_fallback, "_chamar_claude_com_resultado", return_value=resposta_final):
        resultado = claude_fallback.responder_com_fallback_ia("O cliente C007 ainda está ativo?")

    assert resultado["origem"] == "ia"
    assert resultado["encontrado"] is True
    assert resultado["tool"] == "buscar_registro_cliente"
    assert resultado["resultado"]["situacao"] == "Cancelado"
    print("OK   buscar_registro_cliente:", resultado["resposta"])


def caso_fora_do_escopo():
    """Pergunta genuinamente fora do escopo — Claude não chama nenhuma tool."""
    resposta_sem_tool = SimpleNamespace(stop_reason="end_turn", content=[_bloco_texto("...")])
    with patch.object(claude_fallback, "_chamar_claude", return_value=resposta_sem_tool):
        resultado = claude_fallback.responder_com_fallback_ia("Qual a previsão do tempo amanhã?")

    assert resultado == {"origem": "ia", "encontrado": False}
    print("OK   fora do escopo -> não encontrado (sem texto livre inventado)")


def caso_timeout():
    """Simula com_timeout estourando o limite — deve cair em 'não encontrei',
    nunca travar o request nem propagar a exceção pro cliente."""
    from .guardrails import FallbackTimeoutError

    with patch.object(claude_fallback, "com_timeout", side_effect=FallbackTimeoutError("excedeu 8s")):
        resultado = claude_fallback.responder_com_fallback_ia("pergunta qualquer")

    assert resultado == {"origem": "ia", "encontrado": False, "erro": "timeout"}
    print("OK   timeout tratado sem travar:", resultado)


if __name__ == "__main__":
    caso_consultar_metrica()
    caso_buscar_registro_cliente()
    caso_fora_do_escopo()
    caso_timeout()
    print("\nTodos os cenários do item 5 do entregável passaram (com API mockada).")
