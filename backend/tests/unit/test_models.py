from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.enums import FaixaRisco, Plano, Porte, SituacaoCliente, TipoExecucao
from app.models import (
    AtendimentoMensal,
    AvaliacaoRisco,
    Cliente,
    ExecucaoAnalise,
    Situacao,
)

TABELAS = {
    "usuarios",
    "clientes",
    "situacao_clientes",
    "atendimentos_mensais",
    "pesquisas_nps",
    "configuracoes_sinal",
    "acoes_recomendadas",
    "execucoes_analise",
    "avaliacoes_risco",
    "evidencias_risco",
}


def _cliente(cliente_id: str = "C001") -> Cliente:
    return Cliente(
        cliente_id=cliente_id,
        segmento="Saude",
        porte=Porte.MEDIO,
        plano=Plano.AVANCADO,
        valor_mensal=Decimal("10742.00"),
        sla_contratado_h=12,
        inicio_contrato=date(2020, 2, 1),
    )


def _atendimento(mes: date, pct_sla: Decimal | None = Decimal("64.3")) -> AtendimentoMensal:
    return AtendimentoMensal(
        cliente_id="C001",
        mes_ref=mes,
        chamados_abertos=14,
        chamados_criticos=3,
        chamados_reabertos=5,
        chamados_dentro_sla=9,
        pct_sla_cumprido=pct_sla,
        tempo_medio_resolucao_h=Decimal("22.4"),
        reclamacoes_formais=1,
        uso_plataforma_pct=Decimal("74.5"),
        dias_atraso_pagamento=13,
        reunioes_previstas=1,
        reunioes_realizadas=0,
    )


def test_create_all_cria_todas_as_tabelas_do_mvp(app):
    assert TABELAS <= set(inspect(app.state.engine).get_table_names())


def test_atendimento_unico_por_cliente_e_mes(db_session):
    db_session.add(_cliente())
    db_session.add(_atendimento(date(2025, 1, 1)))
    db_session.commit()

    db_session.add(_atendimento(date(2025, 1, 1)))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_pct_sla_nulo_e_enum_como_texto_sao_preservados(db_session):
    db_session.add(_cliente())
    db_session.add(Situacao(cliente_id="C001", situacao=SituacaoCliente.ATIVO))
    db_session.add(_atendimento(date(2025, 2, 1), pct_sla=None))
    db_session.commit()

    atendimento = db_session.query(AtendimentoMensal).one()
    assert atendimento.pct_sla_cumprido is None
    bruto = db_session.execute(text("SELECT porte, plano FROM clientes")).one()
    assert tuple(bruto) == ("MEDIO", "AVANCADO")
    assert db_session.get(Cliente, "C001").situacao.situacao == SituacaoCliente.ATIVO


def test_execucao_conta_clientes_na_fila(db_session):
    db_session.add(_cliente("C001"))
    db_session.add(_cliente("C002"))
    execucao = ExecucaoAnalise(
        tipo=TipoExecucao.PRODUCAO,
        mes_referencia=date(2026, 6, 1),
        versao_modelo="teste",
        parametros_json="{}",
        qtd_clientes_avaliados=2,
    )
    for posicao, cliente_id in ((1, "C001"), (None, "C002")):
        execucao.avaliacoes.append(
            AvaliacaoRisco(
                cliente_id=cliente_id,
                mes_referencia=date(2026, 6, 1),
                score_risco=Decimal("0.4"),
                faixa=FaixaRisco.ATENCAO,
                qtd_dimensoes_afetadas=2,
                receita_em_risco=Decimal("100.00"),
                posicao_fila=posicao,
            )
        )
    db_session.add(execucao)
    db_session.commit()

    assert execucao.qtd_na_fila == 1
