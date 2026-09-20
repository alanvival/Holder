"""
Índice de alerta: diagnóstico do cliente contra a própria história.

Responde "este cliente piorou?". Não confundir com `holder/dominio/strikes/`
(semelhança com quem já cancelou) nem com `holder/dominio/risco/` (score do
modelo treinado) — são três conceitos distintos, ver `CONTEXT.md`.
"""
from .indice import clientes_em_risco
from .pesos import pesos_dos_sinais

__all__ = ["clientes_em_risco", "pesos_dos_sinais"]
