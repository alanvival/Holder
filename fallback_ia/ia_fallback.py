"""
Fallback com IA (tool use) — só entra quando o catálogo determinístico (JS,
no front) não reconhece a pergunta. O modelo nunca calcula ou "lembra" um
número: ele escolhe qual tool rodar, o backend executa a consulta de
verdade contra os dados reais (tools.executar_tool), e só então o modelo
formata a resposta final em cima do resultado real.

Provedor: Groq (API compatível com OpenAI — chat.completions + tool
calling). A arquitetura é a mesma pensada originalmente pra Claude API;
trocar de provedor de novo (ex: voltar pra Anthropic) significa reescrever
só _chamar_modelo, não o resto do fluxo.

O loop é MULTI-TURNO (até MAX_TURNOS_TOOL rodadas): pra perguntas mais
abertas ("diagnóstico geral considerando todos os indicadores"), o modelo
pode legitimamente querer chamar uma tool, olhar o resultado, e decidir
chamar outra antes de escrever a resposta final — um fluxo de 1 turno só
trata isso como sucesso com texto vazio (bug observado em teste manual: a
pergunta batia em consultar_metrica, mas o segundo turno voltava com OUTRA
tool_call em vez de texto, e o content ficava None).

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

MODEL = "openai/gpt-oss-120b"
# gpt-oss é um "reasoning model" — gasta uma parte do orçamento de tokens
# pensando antes de responder, então precisa de mais margem que um modelo
# comum pra sobrar espaço pro texto final (testado: 300 tokens já cortava
# respostas curtas pela metade).
MAX_TOKENS = 2048

# Guardrail contra loop de tool use: no máximo N idas e vindas antes de
# desistir e cair em "não encontrei" — perguntas legítimas resolvem em 1-2.
# Subiu de 4 pra 6 depois de introduzir o encadeamento de tools no system
# prompt (comparação indireta: "o maior cliente do Varejo" precisa de
# listar_clientes x2 + comparar_clientes + texto final = 4 turnos no mínimo,
# sem margem nenhuma se o modelo tropeçar e refizer uma chamada).
MAX_TURNOS_TOOL = 6

SYSTEM_PROMPT = (
    "Você é o mecanismo de resposta de um assistente de consultas sobre uma "
    "base de clientes. Você SÓ pode responder usando os resultados das tools "
    "disponíveis — nunca calcule, estime ou complete um número a partir do seu "
    "conhecimento geral. Se a pergunta não puder ser respondida com nenhuma das "
    "tools disponíveis, não chame nenhuma tool e não tente responder de outra "
    "forma — isso será tratado separadamente pelo sistema. Ao formatar a "
    "resposta final, use o valor exatamente como veio do resultado da tool, "
    "declare o universo considerado (quantos clientes, qual período, quais "
    "filtros), e use formatação brasileira (R$, vírgula decimal).\n\n"
    "Quando uma pergunta exigir informação que nenhuma tool sozinha resolve "
    "— por exemplo, identificar um cliente por uma descrição antes de "
    "comparar ou detalhar algo sobre ele — chame as tools necessárias em "
    "sequência, usando o resultado de uma para montar os parâmetros da "
    "próxima. Só escreva a resposta final depois de ter todos os resultados "
    "reais necessários. Nunca preencha uma lacuna de identificação com um "
    "palpite.\n\n"
    "Datas relativas ('este mês', 'ano passado', 'nos últimos 3 meses') são "
    "sua responsabilidade traduzir para AAAA-MM explícito antes de chamar a "
    "tool — o backend só entende período explícito, nunca texto relativo."
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


def _chamar_modelo(mensagens: list[dict]):
    client = _get_client()
    return client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=mensagens,
        tools=tools_formato_openai(),
        tool_choice="auto",
    )


_MAX_MENSAGENS_HISTORICO = 6  # mesmo teto do front (useAssistant.js#MAX_TROCAS_HISTORICO)


def _sanitizar_historico(historico: list | None) -> list[dict]:
    """Histórico vem do cliente (POST /api/fallback-ia) — nunca confiar
    cegamente: só aceita role user/assistant com content string, descarta
    qualquer outra coisa (não deixa o front injetar um 'system' ou 'tool'
    falso no meio da conversa real)."""
    if not historico:
        return []
    limpo = []
    for item in historico[-_MAX_MENSAGENS_HISTORICO:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            limpo.append({"role": role, "content": content.strip()[:2000]})
    return limpo


def responder_com_fallback_ia(pergunta: str, historico: list | None = None) -> dict:
    """
    Retorna sempre um dict com "origem": "ia" e:
      - {"encontrado": False} quando o modelo não achou tool pra pergunta,
        ou esgotou as rodadas sem escrever uma resposta final (cai no
        mesmo fluxo de "não encontrei" do catálogo);
      - {"encontrado": True, "resposta": str, "tool": str} quando resolveu.
    Nunca deixa o modelo devolver texto livre sem ter passado por tool.

    `historico`: últimas trocas da MESMA conversa (ver
    useAssistant.js#construirHistoricoParaIa) — sem isso, cada pergunta
    chegava sem nenhum contexto anterior, e referências tipo "esse
    cliente"/"e esse outro" nunca resolviam a ninguém (bug reportado ao
    vivo). São só as respostas em TEXTO de turnos passados, não os dados
    brutos das tools — o suficiente pro modelo resolver a referência, sem
    inflar o prompt com JSON de tool antigo.
    """
    inicio = time.monotonic()
    mensagens: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *_sanitizar_historico(historico),
        {"role": "user", "content": pergunta},
    ]
    tools_usadas: list[str] = []
    ultimo_resultado = None

    try:
        for turno in range(MAX_TURNOS_TOOL):
            resposta = com_timeout(_chamar_modelo, mensagens)
            mensagem = resposta.choices[0].message

            if not mensagem.tool_calls:
                tempo_ms = int((time.monotonic() - inicio) * 1000)

                # Nenhuma tool foi chamada em turno nenhum — mesmo que o
                # modelo tenha escrito algo em `content`, é texto livre não
                # fundamentado em dado real. Nunca aceitar isso como
                # resposta: é exatamente o "não invente número" do prompt.
                if not tools_usadas:
                    registrar_chamada(
                        pergunta=pergunta, tool_escolhida=None, sucesso=True, tempo_ms=tempo_ms,
                    )
                    return {"origem": "ia", "encontrado": False}

                texto = (mensagem.content or "").strip()
                if not texto:
                    # Tool(s) já rodaram, mas o modelo voltou sem tool_call
                    # e sem texto — falha real dele, não um "fora do escopo".
                    registrar_chamada(
                        pergunta=pergunta, tool_escolhida=",".join(tools_usadas), sucesso=False,
                        tempo_ms=tempo_ms, origem_erro="resposta_vazia_apos_tool",
                    )
                    return {"origem": "ia", "encontrado": False}

                registrar_chamada(
                    pergunta=pergunta, tool_escolhida=",".join(tools_usadas), sucesso=True, tempo_ms=tempo_ms,
                )
                return {
                    "origem": "ia",
                    "encontrado": True,
                    "resposta": texto,
                    "tool": tools_usadas[-1],
                    "resultado": ultimo_resultado,
                }

            mensagens.append(mensagem.model_dump(exclude_none=True))
            for tool_call in mensagem.tool_calls:
                nome = tool_call.function.name
                tools_usadas.append(nome)
                argumentos = json.loads(tool_call.function.arguments)
                ultimo_resultado = executar_tool(nome, argumentos)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(ultimo_resultado, ensure_ascii=False),
                })

        # Esgotou MAX_TURNOS_TOOL sem chegar a uma resposta em texto.
        registrar_chamada(
            pergunta=pergunta, tool_escolhida=",".join(tools_usadas) or None,
            sucesso=False, tempo_ms=int((time.monotonic() - inicio) * 1000),
            origem_erro="max_turnos_excedido",
        )
        return {"origem": "ia", "encontrado": False}

    except FallbackTimeoutError:
        registrar_chamada(
            pergunta=pergunta, tool_escolhida=",".join(tools_usadas) or None, sucesso=False,
            tempo_ms=int((time.monotonic() - inicio) * 1000), origem_erro="timeout",
        )
        return {"origem": "ia", "encontrado": False, "erro": "timeout"}

    except Exception as exc:  # nunca deixa o backend cair por erro da API
        registrar_chamada(
            pergunta=pergunta, tool_escolhida=",".join(tools_usadas) or None, sucesso=False,
            tempo_ms=int((time.monotonic() - inicio) * 1000), origem_erro=str(exc),
        )
        return {"origem": "ia", "encontrado": False, "erro": str(exc)}
