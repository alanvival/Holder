"""
Cliente do provedor de IA (Groq, API compatível com OpenAI).

O único lugar que conhece a chave, o endpoint e o nome do modelo. Existe
para o fluxo de tool use (`holder/aplicacao/assistente/ia_fallback.py`) não
precisar saber nada disso — trocar de provedor é mexer aqui.
"""
from __future__ import annotations

import os

from groq import Groq

MODELO = "openai/gpt-oss-120b"

# gpt-oss é um "reasoning model" — gasta uma parte do orçamento de tokens
# pensando antes de responder, então precisa de mais margem que um modelo
# comum pra sobrar espaço pro texto final (testado: 300 tokens já cortava
# respostas curtas pela metade).
MAX_TOKENS = 2048

_cliente = None


def obter_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY não configurada — copie .env.example para "
                ".env e preencha com uma chave real."
            )
        _cliente = Groq(api_key=api_key)
    return _cliente


def chamar(mensagens: list[dict], tools: list[dict]):
    """Uma ida ao modelo, com as tools disponíveis e escolha automática."""
    return obter_cliente().chat.completions.create(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        messages=mensagens,
        tools=tools,
        tool_choice="auto",
    )
