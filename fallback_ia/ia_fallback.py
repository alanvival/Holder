"""
Fallback com IA (tool use) — só entra quando o catálogo determinístico (JS,
no front) não reconhece a pergunta. O modelo nunca calcula ou "lembra" um
número: ele escolhe qual tool rodar, o backend executa a consulta de
verdade contra os dados reais (tools.executar_tool), e só então o modelo
formata a resposta final em cima do resultado real.

Provedor: Groq (API compatível com OpenAI — chat.completions + tool
calling). A arquitetura é a mesma pensada originalmente pra Claude API;
trocar de provedor de novo (ex: voltar pra Anthropic) significa reescrever
só _chamar_modelo/_chamar_modelo_com_resultado, não o resto do fluxo.

tool_choice fica sempre "auto" — nunca "required"/força uma tool: forçar
faz o modelo "inventar" parâmetros pra uma tool que não faz sentido pra
pergunta.
"""
from __future__ import annotations

import json
import os
import time

from groq import Groq

from .guardrails import FallbackTimeoutError, com_timeout, registrar_chamada
from .tools import executar_tool, tools_formato_openai

MODEL = "llama-3.3-70b-versatile"
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
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY não configurada — copie .env.example para "
                ".env e preencha com uma chave real."
            )
        _client = Groq(api_key=api_key)
    return _client


def _chamar_modelo(pergunta: str):
    client = _get_client()
    return client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pergunta},
        ],
        tools=tools_formato_openai(),
        tool_choice="auto",
    )


def _chamar_modelo_com_resultado(pergunta: str, mensagem_bruta, tool_call, resultado_real):
    client = _get_client()
    return client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": pergunta},
            mensagem_bruta.model_dump(exclude_none=True),
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultado_real, ensure_ascii=False),
            },
        ],
        tools=tools_formato_openai(),
    )


def responder_com_fallback_ia(pergunta: str) -> dict:
    """
    Retorna sempre um dict com "origem": "ia" e:
      - {"encontrado": False} quando o modelo não achou tool pra pergunta
        (cai no mesmo fluxo de "não encontrei" do catálogo);
      - {"encontrado": True, "resposta": str, "tool": str} quando resolveu.
    Nunca deixa o modelo devolver texto livre sem ter passado por uma tool.
    """
    inicio = time.monotonic()
    tool_escolhida = None
    try:
        resposta = com_timeout(_chamar_modelo, pergunta)
        mensagem = resposta.choices[0].message

        if not mensagem.tool_calls:
            registrar_chamada(
                pergunta=pergunta, tool_escolhida=None, sucesso=True,
                tempo_ms=int((time.monotonic() - inicio) * 1000),
            )
            return {"origem": "ia", "encontrado": False}

        tool_call = mensagem.tool_calls[0]
        tool_escolhida = tool_call.function.name
        argumentos = json.loads(tool_call.function.arguments)
        resultado_real = executar_tool(tool_escolhida, argumentos)

        resposta_final = com_timeout(
            _chamar_modelo_com_resultado, pergunta, mensagem, tool_call, resultado_real,
        )
        texto = resposta_final.choices[0].message.content

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

    except FallbackTimeoutError:
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
