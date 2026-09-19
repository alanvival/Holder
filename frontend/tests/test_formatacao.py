from formatacao import ROTULO_FAIXA, brl, percentual


def test_brl_formata_no_padrao_brasileiro():
    assert brl(1234.5) == "R$ 1.234,50"
    assert brl(275000) == "R$ 275.000,00"
    assert brl(None) == "—"


def test_percentual():
    assert percentual(0.4567) == "46%"
    assert percentual(0.4567, casas=1) == "45,7%"
    assert percentual(None) == "—"


def test_rotulos_de_faixa():
    assert ROTULO_FAIXA["ATENCAO"] == "Atenção"
    assert set(ROTULO_FAIXA) == {"CRITICO", "ATENCAO", "MONITORAR", "SAUDAVEL"}
