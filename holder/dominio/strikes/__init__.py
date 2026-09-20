"""
Strikes: semelhança do cliente ativo com quem já cancelou.

Responde "este cliente se parece com quem saiu?". Não confundir com
`holder/dominio/alerta/` (o cliente piorou em relação a si mesmo?) nem com
`holder/dominio/risco/` (score do modelo treinado) — ver `CONTEXT.md`.
"""
from .benchmark import linhas_de_corte
from .recencia import meses_recentes
from .semelhanca import SINAIS, prever_risco_cancelamento

__all__ = ["SINAIS", "linhas_de_corte", "meses_recentes", "prever_risco_cancelamento"]
