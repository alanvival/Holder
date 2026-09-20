"""
Gera os pesos dos sinais de alerta para o resolvedor em JavaScript.

    python scripts/gerar_pesos_alerta.py

Por que gerar em vez de declarar: os pesos não são escolhidos, são
**calculados** a partir dos fatores de cancelamento (o quanto cada sinal
difere entre clientes ativos e cancelados na base real). Não existe "declarar
peso" — só calcular e propagar.

Antes deste script, o lado JavaScript tinha os oito pesos escritos à mão,
com um comentário admitindo que a sincronia era manual. Enquanto os números
batessem, ninguém notaria; no dia em que a base mudasse, o dashboard e o
assistente passariam a discordar em silêncio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Script solto: rodar `python scripts/x.py` coloca `scripts/` no sys.path, não
# a raiz do repo. (Os testes não precisam disso — `pythonpath = .` no
# pytest.ini resolve lá.)
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from holder.dominio.alerta import pesos_dos_sinais  # noqa: E402
DESTINO = RAIZ / "interface-web" / "src" / "data" / "pesosAlerta.json"

AVISO = (
    "GERADO por scripts/gerar_pesos_alerta.py a partir de "
    "holder/dominio/alerta/pesos.py. Não editar à mão: os pesos vêm dos "
    "fatores de cancelamento calculados sobre a base real."
)


def gerar() -> dict:
    return {"_gerado": AVISO, "pesos": pesos_dos_sinais()}


def main() -> None:
    conteudo = gerar()
    DESTINO.write_text(
        json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Pesos gravados em {DESTINO.relative_to(RAIZ)}:")
    for sinal, peso in conteudo["pesos"].items():
        print(f"  {peso:>4}  {sinal}")


if __name__ == "__main__":
    main()
