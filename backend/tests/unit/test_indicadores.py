import math
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.services.risco.indicadores import (
    COLUNAS_SAIDA,
    SENTIDO_PIORA,
    calcular_indicadores,
    somar_meses,
)

JAN25 = date(2025, 1, 1)
PADRAO = {
    "chamados_abertos": 5,
    "chamados_criticos": 1,
    "chamados_reabertos": 1,
    "pct_sla_cumprido": 80.0,
    "tempo_medio_resolucao_h": 12.0,
    "reclamacoes_formais": 0,
    "uso_plataforma_pct": 80.0,
    "dias_atraso_pagamento": 0,
    "reunioes_previstas": 1,
    "reunioes_realizadas": 1,
}
CLIENTES = pd.DataFrame(
    [{"cliente_id": "C001", "sla_contratado_h": 12}, {"cliente_id": "C002", "sla_contratado_h": 24}]
)
SEM_NPS = pd.DataFrame(columns=["cliente_id", "mes_ref", "respondeu", "nota_nps"])


def _atendimentos(n: int = 12, cliente_id: str = "C001", inicio: date = JAN25, **series):
    """n meses a partir de `inicio`; cada kwarg é a lista de n valores de uma coluna."""
    linhas = []
    for i in range(n):
        linha = {"cliente_id": cliente_id, "mes_ref": somar_meses(inicio, i)}
        for coluna, padrao in PADRAO.items():
            linha[coluna] = series[coluna][i] if coluna in series else padrao
        linhas.append(linha)
    return pd.DataFrame(linhas)


def _valor(df: pd.DataFrame, variavel: str, coluna: str, cliente_id: str = "C001"):
    linha = df[(df["cliente_id"] == cliente_id) & (df["variavel"] == variavel)]
    assert len(linha) == 1
    return linha.iloc[0][coluna]


def test_somar_meses_vira_o_ano():
    assert somar_meses(date(2025, 11, 1), 3) == date(2026, 2, 1)
    assert somar_meses(date(2025, 3, 1), -3) == date(2024, 12, 1)


def test_saida_tem_uma_linha_por_variavel():
    resultado = calcular_indicadores(_atendimentos(), SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert list(resultado.columns) == COLUNAS_SAIDA
    assert set(resultado["variavel"]) == set(SENTIDO_PIORA)
    assert len(resultado) == len(SENTIDO_PIORA)


def test_media_3m_linha_base_6m_e_variacao():
    at = _atendimentos(chamados_reabertos=list(range(1, 13)))
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "valor_mes") == 12
    assert _valor(resultado, "chamados_reabertos", "media_3m") == pytest.approx(11.0)
    assert _valor(resultado, "chamados_reabertos", "soma_3m") == pytest.approx(33.0)
    assert _valor(resultado, "chamados_reabertos", "linha_base_6m") == pytest.approx(6.5)
    assert _valor(resultado, "chamados_reabertos", "variacao_pct") == pytest.approx(4.5 / 6.5)


def test_variacao_usa_denominador_minimo_quando_base_e_zero():
    at = _atendimentos(chamados_reabertos=[0] * 9 + [1, 1, 1])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "variacao_pct") == pytest.approx(2.0)


def test_media_ignora_nulos_de_sla():
    at = _atendimentos(pct_sla_cumprido=[80.0] * 9 + [80.0, None, 60.0])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "pct_sla_cumprido", "media_3m") == pytest.approx(70.0)


def test_aceita_decimal_e_none_vindos_do_banco():
    valores = [Decimal("80.0")] * 11 + [None]
    at = _atendimentos(pct_sla_cumprido=valores)
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert math.isnan(_valor(resultado, "pct_sla_cumprido", "valor_mes"))
    assert _valor(resultado, "pct_sla_cumprido", "media_3m") == pytest.approx(80.0)


def test_mes_futuro_nao_vaza_para_o_calculo():
    doze = _atendimentos(12, chamados_reabertos=list(range(1, 13)))
    treze = _atendimentos(13, chamados_reabertos=list(range(1, 13)) + [99])
    mes = somar_meses(JAN25, 11)

    pd.testing.assert_frame_equal(
        calcular_indicadores(doze, SEM_NPS, CLIENTES, mes),
        calcular_indicadores(treze, SEM_NPS, CLIENTES, mes),
    )


def test_meses_consecutivos_de_piora_respeitam_o_sentido():
    at = _atendimentos(
        chamados_reabertos=[1] * 9 + [5, 5, 5],
        uso_plataforma_pct=[80.0] * 10 + [60.0, 60.0],
    )
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert _valor(resultado, "chamados_reabertos", "meses_consecutivos_piora") == 3
    assert _valor(resultado, "uso_plataforma_pct", "meses_consecutivos_piora") == 2
    assert _valor(resultado, "dias_atraso_pagamento", "meses_consecutivos_piora") == 0


def test_derivados_ficam_nulos_sem_chamado_ou_sem_reuniao_prevista():
    at = _atendimentos(chamados_abertos=[5] * 11 + [0], reunioes_previstas=[1] * 11 + [0])
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, somar_meses(JAN25, 11))

    assert math.isnan(_valor(resultado, "taxa_reabertura", "valor_mes"))
    assert math.isnan(_valor(resultado, "tempo_resolucao_vs_sla", "valor_mes"))
    assert math.isnan(_valor(resultado, "pct_reunioes_realizadas", "valor_mes"))
    # tempo 12h / SLA 12h = 1,0 nos meses anteriores
    assert _valor(resultado, "tempo_resolucao_vs_sla", "media_3m") == pytest.approx(1.0)


def test_nps_nota_variacao_e_silencio():
    pesquisas = pd.DataFrame(
        [
            {"cliente_id": "C001", "mes_ref": date(2025, 3, 1), "respondeu": 1, "nota_nps": 9},
            {"cliente_id": "C001", "mes_ref": date(2025, 6, 1), "respondeu": 1, "nota_nps": 6},
            {"cliente_id": "C001", "mes_ref": date(2025, 9, 1), "respondeu": 0, "nota_nps": None},
            {"cliente_id": "C001", "mes_ref": date(2025, 12, 1), "respondeu": 0, "nota_nps": None},
        ]
    )
    resultado = calcular_indicadores(_atendimentos(), pesquisas, CLIENTES, date(2025, 12, 1))

    assert _valor(resultado, "nps_nota", "valor_mes") == 6
    assert _valor(resultado, "nps_variacao", "valor_mes") == -3
    assert _valor(resultado, "nps_sem_resposta_consecutivas", "valor_mes") == 2


def test_silencio_so_conta_se_ja_respondeu_antes():
    pesquisas = pd.DataFrame(
        [{"cliente_id": "C001", "mes_ref": date(2025, 3, 1), "respondeu": 0, "nota_nps": None}]
    )
    resultado = calcular_indicadores(_atendimentos(), pesquisas, CLIENTES, date(2025, 12, 1))

    assert _valor(resultado, "nps_sem_resposta_consecutivas", "valor_mes") == 0
    assert math.isnan(_valor(resultado, "nps_nota", "valor_mes"))


def test_historico_curto_deixa_base_e_variacao_nulas():
    resultado = calcular_indicadores(_atendimentos(3), SEM_NPS, CLIENTES, date(2025, 3, 1))

    assert math.isnan(_valor(resultado, "chamados_reabertos", "linha_base_6m"))
    assert math.isnan(_valor(resultado, "chamados_reabertos", "variacao_pct"))
    assert _valor(resultado, "chamados_reabertos", "meses_consecutivos_piora") == 0


def test_cliente_sem_dados_ate_o_mes_fica_de_fora():
    at = pd.concat(
        [_atendimentos(12), _atendimentos(3, cliente_id="C002", inicio=date(2026, 1, 1))]
    )
    resultado = calcular_indicadores(at, SEM_NPS, CLIENTES, date(2025, 12, 1))

    assert set(resultado["cliente_id"]) == {"C001"}
    assert calcular_indicadores(at, SEM_NPS, CLIENTES, date(2024, 12, 1)).empty
