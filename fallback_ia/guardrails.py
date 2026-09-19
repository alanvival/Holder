"""
Guardrails obrigatórios do prompt de fallback: timeout na chamada à API,
rate limit por sessão, e log estruturado de toda chamada que cai no
fallback (alimenta a área administrativa — perguntas frequentes no
fallback são candidatas a virar métrica oficial no catálogo).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from threading import Lock

TIMEOUT_SEGUNDOS = 8
RATE_LIMIT_MAX_CHAMADAS = 5
RATE_LIMIT_JANELA_SEGUNDOS = 60

# --- Log estruturado -------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("fallback_ia")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "fallback_ia.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[fallback_ia] %(message)s"))
    logger.addHandler(console)


def registrar_chamada(*, pergunta: str, tool_escolhida: str | None, sucesso: bool, tempo_ms: int, origem_erro: str | None = None):
    logger.info(
        "pergunta=%r tool=%r sucesso=%s tempo_ms=%d erro=%r",
        pergunta, tool_escolhida, sucesso, tempo_ms, origem_erro,
    )


# --- Timeout -----------------------------------------------------------

_executor = ThreadPoolExecutor(max_workers=8)


class FallbackTimeoutError(Exception):
    pass


def com_timeout(func, *args, segundos: int = TIMEOUT_SEGUNDOS, **kwargs):
    """Roda func(*args, **kwargs) num worker à parte e derruba se passar do
    limite — a chamada à API real continua rodando em background (o SDK não
    tem cancelamento cooperativo), mas o usuário não fica esperando."""
    future = _executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=segundos)
    except FuturesTimeoutError as exc:
        raise FallbackTimeoutError(f"Chamada excedeu {segundos}s") from exc


# --- Rate limit por sessão ----------------------------------------------

_chamadas_por_sessao: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def limite_excedido(sessao_id: str) -> bool:
    """True se essa sessão já bateu o teto de chamadas de fallback na
    janela — protege contra uma sessão sozinha gerar custo descontrolado."""
    agora = time.monotonic()
    with _lock:
        fila = _chamadas_por_sessao[sessao_id]
        while fila and agora - fila[0] > RATE_LIMIT_JANELA_SEGUNDOS:
            fila.popleft()
        if len(fila) >= RATE_LIMIT_MAX_CHAMADAS:
            return True
        fila.append(agora)
        return False
