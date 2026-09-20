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

# O prompt original pedia "~8s"; subiu pra 15s depois de observar timeouts
# reais em perguntas cujo resultado de tool é mais volumoso (ex:
# clientes_em_alerta devolvendo vários clientes com listas de sinais cada) —
# gpt-oss é um reasoning model e gasta mais tempo "pensando" sobre payloads
# maiores antes de escrever a resposta final. Subiu de novo pra 20s depois
# de observar timeouts intermitentes mesmo em chamadas simples (ex:
# listar_clientes com filtro único) — variância de latência da API, não bug
# de lógica: a mesma pergunta que estourou o timeout respondeu certo ao
# tentar de novo.
TIMEOUT_SEGUNDOS = 20
RATE_LIMIT_MAX_CHAMADAS = 5
RATE_LIMIT_JANELA_SEGUNDOS = 60

# --- Log estruturado -------------------------------------------------

LOG_DIR = Path(__file__).resolve().parents[3] / "dados" / "gerado" / "logs"

logger = logging.getLogger("fallback_ia")


def configurar_log():
    """Cria o diretório de log e liga os handlers. Chamada na primeira
    gravação, não no import: antes, só importar este módulo já criava a
    pasta `logs/` e abria um arquivo — efeito colateral em disco pago por
    qualquer um que importasse o pacote, inclusive a suíte de testes."""
    if logger.handlers:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_DIR / "fallback_ia.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[fallback_ia] %(message)s"))
    logger.addHandler(console)


def registrar_chamada(*, pergunta: str, tool_escolhida: str | None, sucesso: bool, tempo_ms: int, origem_erro: str | None = None):
    configurar_log()
    logger.info(
        "pergunta=%r tool=%r sucesso=%s tempo_ms=%d erro=%r",
        pergunta, tool_escolhida, sucesso, tempo_ms, origem_erro,
    )


# --- Timeout -----------------------------------------------------------

# Criar o executor no import é barato e não é efeito colateral observável:
# o ThreadPoolExecutor só cria thread no primeiro submit.
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
