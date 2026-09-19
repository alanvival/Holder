from app.core.enums import FaixaRisco
from app.services.risco.priorizacao import ItemAvaliado, priorizar


def _item(cliente_id: str, valor: float, score: float, faixa: FaixaRisco) -> ItemAvaliado:
    return ItemAvaliado(cliente_id=cliente_id, valor_mensal=valor, score=score, faixa=faixa)


def test_receita_em_risco_e_score_vezes_valor():
    [item] = priorizar([_item("C1", 10000.0, 0.4, FaixaRisco.ATENCAO)], capacidade=10)

    assert item.receita_em_risco == 4000.0


def test_ordena_por_faixa_e_depois_por_receita():
    itens = [
        _item("ATENCAO_GRANDE", 30000.0, 0.4, FaixaRisco.ATENCAO),
        _item("CRITICO_PEQUENO", 3000.0, 0.6, FaixaRisco.CRITICO),
        _item("ATENCAO_MEDIO", 10000.0, 0.4, FaixaRisco.ATENCAO),
        _item("SAUDAVEL", 50000.0, 0.0, FaixaRisco.SAUDAVEL),
    ]

    resultado = priorizar(itens, capacidade=10)

    assert [i.cliente_id for i in resultado] == [
        "CRITICO_PEQUENO",
        "ATENCAO_GRANDE",
        "ATENCAO_MEDIO",
        "SAUDAVEL",
    ]
    assert [i.posicao_fila for i in resultado] == [1, 2, 3, None]


def test_capacidade_limita_a_fila_e_monitorar_fica_de_fora():
    itens = [_item(f"C{i}", 1000.0 * (i + 1), 0.4, FaixaRisco.ATENCAO) for i in range(5)]
    itens.append(_item("M", 99999.0, 0.2, FaixaRisco.MONITORAR))

    resultado = priorizar(itens, capacidade=3)

    na_fila = [i for i in resultado if i.posicao_fila is not None]
    assert [i.posicao_fila for i in na_fila] == [1, 2, 3]
    assert [i.cliente_id for i in na_fila] == ["C4", "C3", "C2"]
    assert next(i for i in resultado if i.cliente_id == "M").posicao_fila is None


def test_nao_altera_a_lista_de_entrada():
    original = _item("C1", 1000.0, 0.4, FaixaRisco.ATENCAO)

    priorizar([original], capacidade=10)

    assert original.posicao_fila is None
    assert original.receita_em_risco == 0.0
