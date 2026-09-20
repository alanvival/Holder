"""
Teste de contrato entre os dois resolvedores de métrica.

A duplicação do resolvedor (Python e JavaScript) é deliberada — é o que
mantém o catálogo respondendo no navegador sem backend no ar, ver
`docs/adr/0003-resolvedor-de-metricas-duplicado-de-proposito.md`. O preço
disso é que os dois podem divergir em silêncio, e é este arquivo que
transforma a divergência em falha.

O lado JavaScript dos mesmos números está em
`interface-web/scripts/testar-metricas.mjs` (`npm run test:metricas`).
Os dois leem a MESMA definição declarativa; o que cada um implementa é só
as cinco agregações nomeadas.
"""
import json
from pathlib import Path

import pytest

from holder.dominio.metricas.definicoes import ARQUIVO, METRICAS

RAIZ = Path(__file__).resolve().parent.parent
RESOLVEDOR_JS = RAIZ / "interface-web" / "src" / "engine" / "metricas.js"
PESOS_GERADOS = RAIZ / "interface-web" / "src" / "data" / "pesosAlerta.json"

AGREGACOES_VALIDAS = {
    "media", "media_ponderada", "razao_soma", "proporcao_linhas", "soma",
    "antiguidade_dias", "nps",
}


@pytest.fixture(scope="module")
def entradas():
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))["metricas"]


def test_o_catalogo_python_vem_do_arquivo_compartilhado(entradas):
    ids_do_arquivo = {e["id"] for e in entradas}
    assert set(METRICAS.keys()) == ids_do_arquivo


def test_toda_agregacao_declarada_e_implementada(entradas):
    """Se alguém adicionar uma métrica com agregação nova, os dois lados
    precisam implementá-la — este teste pega o lado Python, e o
    `npm run test:metricas` pega o outro."""
    for entrada in entradas:
        assert entrada["agregacao"] in AGREGACOES_VALIDAS, (
            f"métrica '{entrada['id']}' usa agregação desconhecida: {entrada['agregacao']}"
        )
        if "leitura_alternativa" in entrada:
            assert entrada["leitura_alternativa"]["agregacao"] in AGREGACOES_VALIDAS


def test_o_resolvedor_js_le_o_arquivo_compartilhado():
    """Se alguém reintroduzir um catálogo escrito à mão no JavaScript, os
    ids voltam a poder divergir — e foi exatamente isso que aconteceu antes
    (quatro ids diferentes entre os lados)."""
    js = RESOLVEDOR_JS.read_text(encoding="utf-8")
    assert "definicoes_metricas.json" in js, (
        "metricas.js não importa mais a fonte única de definições"
    )
    assert "definicoesMetricas.metricas.map(montarDefinicao)" in js, (
        "metricas.js não monta mais METRICAS a partir do arquivo compartilhado"
    )


def test_os_pesos_do_alerta_sao_gerados_e_estao_em_sincronia():
    """Os pesos do índice de alerta no lado JavaScript vêm de um arquivo
    gerado por `python scripts/gerar_pesos_alerta.py`. Este teste falha se
    o arquivo estiver desatualizado em relação ao cálculo atual."""
    from holder.dominio.alerta import pesos_dos_sinais

    assert PESOS_GERADOS.exists(), (
        f"{PESOS_GERADOS.name} não existe — rode `python scripts/gerar_pesos_alerta.py`"
    )
    gravados = json.loads(PESOS_GERADOS.read_text(encoding="utf-8"))["pesos"]
    calculados = pesos_dos_sinais()

    assert gravados == calculados, (
        "os pesos gravados divergem do cálculo atual — rode "
        "`python scripts/gerar_pesos_alerta.py`.\n"
        f"gravados:   {gravados}\ncalculados: {calculados}"
    )


def test_o_js_nao_tem_mais_pesos_escritos_a_mao():
    banco_js = (RAIZ / "interface-web" / "src" / "data" / "inovaappsDatabase.js").read_text(encoding="utf-8")
    assert "pesosAlerta.pesos" in banco_js, "inovaappsDatabase.js não lê mais os pesos gerados"
    assert "'Mais chamados críticos': 83" not in banco_js, (
        "voltaram pesos hardcoded ao JavaScript"
    )
