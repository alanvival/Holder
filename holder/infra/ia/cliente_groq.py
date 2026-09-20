"""
Cliente do provedor de IA (Groq, API compatível com OpenAI).

O único lugar que conhece a chave, o endpoint e o nome do modelo. Existe
para o fluxo de tool use (`holder/aplicacao/assistente/ia_fallback.py`) não
precisar saber nada disso — trocar de provedor é mexer aqui.
"""
from __future__ import annotations

import os

from groq import Groq

MODELO = "openai/gpt-oss-20b"
# gpt-oss-120b media 40-223s por pergunta de 1 tool só, ao vivo (reasoning
# model — gasta uma fatia do orçamento de tokens "pensando" antes de
# responder). Troca pra llama-3.3-70b-versatile (sem essa etapa) falhou:
# esta conta Groq só tem acesso à família gpt-oss (client.models.list()).
# gpt-oss-20b é a mesma arquitetura do 120b, ~6x menor — ainda "pensa",
# mas bem mais rápido nisso (confirmado ao vivo: ~18-29s no mesmo caso).
MAX_TOKENS = 1024

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
