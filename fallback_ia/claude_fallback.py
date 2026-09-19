"""
Fallback com a Claude API (tool use) — só entra quando o catálogo
determinístico (JS, no front) não reconhece a pergunta. A Claude nunca
calcula ou "lembra" um número: ela escolhe qual tool rodar, o backend
executa a consulta de verdade contra os dados reais (tools.executar_tool),
e só then a Claude formata a resposta final em cima do resultado real.

tool_choice fica sempre "auto" — nunca "any": forçar uma tool faz a Claude
inventar parâmetros pra uma tool que não faz sentido pra pergunta.
"""
from __future__ import annotations

import os
import time

import anthropic

from .guardrails import FallbackTimeoutError, com_timeout, registrar_chamada
from .tools import TOOLS, executar_tool

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "Você é o mecanismo de resposta de um assistente de consultas sobre uma "
    "base de clientes. Você SÓ pode responder usando os resultados das tools "
    "disponíveis — nunca calcule, estime ou complete um número a partir do seu "
    "conhecimento geral. Se a pergunta não puder ser respondida com nenhuma das "
    "tools disponíveis, não chame nenhuma tool e não tente responder de outra "
    "forma — isso será tratado separadamente pelo sistema. Ao formatar a "
    "resposta final, use o valor exatamente como veio do resultado da tool, "
    "declare o universo considerado (quantos clientes, qual período, quais "
    "filtros), e use formatação brasileira (R$, vírgula decimal)."
)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada — copie .env.example para "
                ".env e preencha com uma chave real."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _chamar_claude(pergunta: str):
    client = _get_client()
    return client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": pergunta}],
    )


def _chamar_claude_com_resultado(pergunta: str, resposta_bruta, bloco_tool, resultado_real):
    client = _get_client()
    return client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=[
            {"role": "user", "content": pergunta},
            {"role": "assistant", "content": resposta_bruta.content},
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": bloco_tool.id, "content": str(resultado_real)}
                ],
            },
        ],
    )


def responder_com_fallback_ia(pergunta: str) -> dict:
    """
    Retorna sempre um dict com "origem": "ia" e:
      - {"encontrado": False} quando a Claude não achou tool pra pergunta
        (cai no mesmo fluxo de "não encontrei" do catálogo);
      - {"encontrado": True, "resposta": str, "tool": str} quando resolveu.
    Nunca deixa a Claude devolver texto livre sem ter passado por uma tool.
    """
    inicio = time.monotonic()
    tool_escolhida = None
    try:
        resposta = com_timeout(_chamar_claude, pergunta)

        if resposta.stop_reason != "tool_use":
            registrar_chamada(
                pergunta=pergunta, tool_escolhida=None, sucesso=True,
                tempo_ms=int((time.monotonic() - inicio) * 1000),
            )
            return {"origem": "ia", "encontrado": False}

        bloco_tool = next(b for b in resposta.content if b.type == "tool_use")
        tool_escolhida = bloco_tool.name
        resultado_real = executar_tool(bloco_tool.name, bloco_tool.input)

        resposta_final = com_timeout(
            _chamar_claude_com_resultado, pergunta, resposta, bloco_tool, resultado_real,
        )
        texto = next(b.text for b in resposta_final.content if b.type == "text")

        registrar_chamada(
            pergunta=pergunta, tool_escolhida=tool_escolhida, sucesso=True,
            tempo_ms=int((time.monotonic() - inicio) * 1000),
        )
        return {
            "origem": "ia",
            "encontrado": True,
            "resposta": texto,
            "tool": tool_escolhida,
            "resultado": resultado_real,
        }

    except FallbackTimeoutError as exc:
        registrar_chamada(
            pergunta=pergunta, tool_escolhida=tool_escolhida, sucesso=False,
            tempo_ms=int((time.monotonic() - inicio) * 1000), origem_erro="timeout",
        )
        return {"origem": "ia", "encontrado": False, "erro": "timeout"}

    except Exception as exc:  # nunca deixa o backend cair por erro da API
        registrar_chamada(
            pergunta=pergunta, tool_escolhida=tool_escolhida, sucesso=False,
            tempo_ms=int((time.monotonic() - inicio) * 1000), origem_erro=str(exc),
        )
        return {"origem": "ia", "encontrado": False, "erro": str(exc)}
