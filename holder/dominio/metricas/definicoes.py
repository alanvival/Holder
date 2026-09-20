"""
Carrega o catálogo de métricas a partir de `definicoes_metricas.json`.

O JSON é a **fonte única**, lida também pelo resolvedor em JavaScript. Este
módulo só traduz cada entrada declarativa para a função que a calcula,
usando as cinco agregações nomeadas de `agregacoes.py` — as mesmas cinco que
o lado JS implementa.

Antes, o catálogo estava escrito duas vezes (uma em Python, uma em JS), com
quatro ids divergentes. Ver
`docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md`.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import agregacoes as ag
from .nps import calcular_nps

ARQUIVO = Path(__file__).resolve().parent / "definicoes_metricas.json"

PLANO_LABELS = {"Essencial": "Essencial", "Avancado": "Avançado", "Enterprise": "Enterprise"}
PORTE_LABELS = {"Pequeno": "Pequeno", "Medio": "Médio", "Grande": "Grande"}

OPERADORES = {
    ">": lambda serie, valor: serie > valor,
    ">=": lambda serie, valor: serie >= valor,
    "<": lambda serie, valor: serie < valor,
    "<=": lambda serie, valor: serie <= valor,
    "==": lambda serie, valor: serie == valor,
}


def _montar_filtro_linha(spec: dict):
    """Traduz {"campo": x, "operador": ">", "valor": 0} numa função de
    filtro. As três métricas que usam filtro de linha usam exatamente esta
    forma, nos dois lados."""
    comparar = OPERADORES[spec["operador"]]
    campo, valor = spec["campo"], spec["valor"]
    return lambda df: df[comparar(df[campo], valor)]


def _montar_calculo(entrada: dict):
    """A função que calcula a métrica, a partir da agregação declarada."""
    agregacao = entrada["agregacao"]

    if agregacao == "media":
        campo = entrada["campo"]
        return lambda df: ag.media(df[campo])
    if agregacao == "soma":
        campo = entrada["campo"]
        return lambda df: ag.soma(df[campo])
    if agregacao == "media_ponderada":
        campo, peso = entrada["campo"], entrada["campo_peso"]
        return lambda df: ag.media_ponderada(df, campo, peso)
    if agregacao == "razao_soma":
        num, den = entrada["campo_numerador"], entrada["campo_denominador"]
        return lambda df: ag.razao_soma(df, num, den)
    if agregacao == "proporcao_linhas":
        campo, valor = entrada["campo"], entrada["valor"]
        return lambda df: float((df[campo] == valor).mean()) if len(df) else None
    if agregacao == "antiguidade_dias":
        return ag.antiguidade_dias
    if agregacao == "nps":
        return calcular_nps

    raise ValueError(f"Agregação desconhecida em definicoes_metricas.json: {agregacao!r}")


@lru_cache(maxsize=1)
def carregar() -> dict:
    """O catálogo, indexado por id. Uma leitura por processo."""
    entradas = json.loads(ARQUIVO.read_text(encoding="utf-8"))["metricas"]

    catalogo = {}
    for entrada in entradas:
        definicao = {
            "rotulo": entrada["rotulo"],
            "aba": entrada["aba"],
            "formato": entrada["formato"],
            "agregacao": entrada["agregacao"],
            "calcular": _montar_calculo(entrada),
        }
        if entrada.get("escala100"):
            definicao["escala100"] = True
        if "filtro_linha" in entrada:
            definicao["filtro_linha"] = _montar_filtro_linha(entrada["filtro_linha"])
        if "leitura_alternativa" in entrada:
            alt = entrada["leitura_alternativa"]
            definicao["leitura_alternativa"] = {
                "rotulo": alt["rotulo"],
                "calcular": _montar_calculo(alt),
            }
        catalogo[entrada["id"]] = definicao

    return catalogo


class _Catalogo(dict):
    """Fachada que mantém `METRICAS[id]`, `in` e iteração funcionando com
    carga preguiçosa — importar este módulo não lê o JSON."""

    def _dados(self):
        return carregar()

    def __getitem__(self, chave):
        return self._dados()[chave]

    def __contains__(self, chave):
        return chave in self._dados()

    def __iter__(self):
        return iter(self._dados())

    def __len__(self):
        return len(self._dados())

    def get(self, chave, padrao=None):
        return self._dados().get(chave, padrao)

    def keys(self):
        return self._dados().keys()

    def items(self):
        return self._dados().items()

    def values(self):
        return self._dados().values()


METRICAS = _Catalogo()
