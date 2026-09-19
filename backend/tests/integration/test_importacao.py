import io
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.core.enums import ClassificacaoNPS, Plano, Porte, SituacaoCliente
from app.core.exceptions import ImportacaoInvalidaError
from app.models import (
    AcaoRecomendada,
    AtendimentoMensal,
    Cliente,
    ConfiguracaoSinal,
    PesquisaNps,
    Situacao,
)
from app.services.fabrica import criar_importacao_service


def _contar(sessao, modelo) -> int:
    return sessao.scalar(select(func.count()).select_from(modelo))


def _xlsx(abas: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        for nome, df in abas.items():
            df.to_excel(escritor, sheet_name=nome, index=False)
    return buffer.getvalue()


def _abas_reais(caminho_xlsx) -> dict[str, pd.DataFrame]:
    abas = pd.read_excel(caminho_xlsx, sheet_name=None)
    nomes = ("clientes", "atendimento_mensal", "pesquisas_nps", "situacao_clientes")
    return {nome: abas[nome] for nome in nomes}


@pytest.fixture
def service(db_session, settings):
    return criar_importacao_service(db_session, settings)


def test_importa_base_real_com_contagens_esperadas(service, db_session, caminho_xlsx):
    relatorio = service.importar(caminho_xlsx)

    assert relatorio.contagens == {
        "clientes": 80,
        "situacao_clientes": 80,
        "atendimentos_mensais": 1295,
        "pesquisas_nps": 422,
    }
    assert relatorio.avisos == []
    assert _contar(db_session, Cliente) == 80
    assert _contar(db_session, AtendimentoMensal) == 1295
    cancelados = db_session.scalar(
        select(func.count()).where(Situacao.situacao == SituacaoCliente.CANCELADO)
    )
    assert cancelados == 22


def test_reimportar_nao_duplica(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    service.importar(caminho_xlsx.read_bytes())

    assert _contar(db_session, Cliente) == 80
    assert _contar(db_session, AtendimentoMensal) == 1295
    assert _contar(db_session, PesquisaNps) == 422


def test_preserva_nulos_e_normaliza_enums_e_meses(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)

    sla_nulos = db_session.scalar(
        select(func.count()).where(AtendimentoMensal.pct_sla_cumprido.is_(None))
    )
    assert sla_nulos == 23
    c002 = db_session.get(Cliente, "C002")
    assert (c002.porte, c002.plano) == (Porte.MEDIO, Plano.AVANCADO)
    assert c002.inicio_contrato == date(2020, 2, 1)
    sem_resposta = db_session.scalars(
        select(PesquisaNps).where(PesquisaNps.classificacao_nps == ClassificacaoNPS.SEM_RESPOSTA)
    ).all()
    assert len(sem_resposta) == 84
    assert all(p.nota_nps is None and p.respondeu is False for p in sem_resposta)
    meses = db_session.scalars(select(AtendimentoMensal.mes_ref).distinct()).all()
    assert all(m.day == 1 for m in meses)
    assert max(meses) == date(2026, 6, 1)
    cancelado = db_session.scalar(
        select(Situacao).where(Situacao.situacao == SituacaoCliente.CANCELADO).limit(1)
    )
    assert cancelado.mes_cancelamento is not None and cancelado.mes_cancelamento.day == 1


def test_importacao_cria_catalogo_seed_uma_vez(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    service.importar(caminho_xlsx)

    assert _contar(db_session, ConfiguracaoSinal) == 10
    assert _contar(db_session, AcaoRecomendada) == 6
    reclamacoes = db_session.scalar(
        select(ConfiguracaoSinal).where(ConfiguracaoSinal.codigo == "RECLAMACOES")
    )
    assert reclamacoes.metrica == "soma_3m"
    assert float(reclamacoes.peso) == pytest.approx(0.10)
    assert reclamacoes.persistencia_min_meses == 2


def test_arquivo_invalido_nao_apaga_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)

    with pytest.raises(ImportacaoInvalidaError, match="xlsx"):
        service.importar(b"isto nao e um xlsx")

    assert _contar(db_session, Cliente) == 80


def test_coluna_faltando_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["clientes"] = abas["clientes"].drop(columns=["plano"])

    with pytest.raises(ImportacaoInvalidaError, match="plano"):
        service.importar(_xlsx(abas))


def test_aba_faltando_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    del abas["pesquisas_nps"]

    with pytest.raises(ImportacaoInvalidaError, match="pesquisas_nps"):
        service.importar(_xlsx(abas))


def test_enum_invalido_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["clientes"].loc[0, "porte"] = "Gigante"

    with pytest.raises(ImportacaoInvalidaError, match="Gigante"):
        service.importar(_xlsx(abas))


def test_texto_em_coluna_inteira_gera_422_e_preserva_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"]["chamados_abertos"] = abas["atendimento_mensal"][
        "chamados_abertos"
    ].astype(object)
    abas["atendimento_mensal"].loc[0, "chamados_abertos"] = "abc"

    with pytest.raises(ImportacaoInvalidaError, match="chamados_abertos"):
        service.importar(_xlsx(abas))

    assert _contar(db_session, Cliente) == 80


def test_texto_em_coluna_decimal_gera_422_e_preserva_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"]["tempo_medio_resolucao_h"] = abas["atendimento_mensal"][
        "tempo_medio_resolucao_h"
    ].astype(object)
    abas["atendimento_mensal"].loc[0, "tempo_medio_resolucao_h"] = "n/d"

    with pytest.raises(ImportacaoInvalidaError, match="tempo_medio_resolucao_h"):
        service.importar(_xlsx(abas))

    assert _contar(db_session, Cliente) == 80


def test_valor_mensal_vazio_gera_422_e_preserva_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    abas = _abas_reais(caminho_xlsx)
    abas["clientes"].loc[0, "valor_mensal"] = None

    with pytest.raises(ImportacaoInvalidaError, match="valor_mensal"):
        service.importar(_xlsx(abas))

    assert _contar(db_session, Cliente) == 80


def test_mes_ref_vazio_gera_422_e_preserva_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"].loc[0, "mes_ref"] = None

    with pytest.raises(ImportacaoInvalidaError, match="mes_ref"):
        service.importar(_xlsx(abas))

    assert _contar(db_session, Cliente) == 80


def test_inteiro_nao_integral_gera_422_e_preserva_dados(service, db_session, caminho_xlsx):
    service.importar(caminho_xlsx)
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"]["chamados_abertos"] = abas["atendimento_mensal"][
        "chamados_abertos"
    ].astype(float)
    abas["atendimento_mensal"].loc[0, "chamados_abertos"] = 3.7

    with pytest.raises(ImportacaoInvalidaError, match="chamados_abertos"):
        service.importar(_xlsx(abas))

    assert _contar(db_session, Cliente) == 80


def test_situacao_faltando_para_cliente_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    primeiro_id = abas["clientes"].loc[0, "cliente_id"]
    abas["situacao_clientes"] = abas["situacao_clientes"][
        abas["situacao_clientes"]["cliente_id"] != primeiro_id
    ]

    with pytest.raises(ImportacaoInvalidaError, match=f"situação.*{primeiro_id}"):
        service.importar(_xlsx(abas))


def test_linha_duplicada_gera_erro_claro(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    abas["atendimento_mensal"] = pd.concat(
        [abas["atendimento_mensal"], abas["atendimento_mensal"].head(1)]
    )

    with pytest.raises(ImportacaoInvalidaError, match="duplicad"):
        service.importar(_xlsx(abas))


def test_contagens_diferentes_geram_avisos(service, caminho_xlsx):
    abas = _abas_reais(caminho_xlsx)
    primeiros = set(abas["clientes"]["cliente_id"].head(10))
    abas = {nome: df[df["cliente_id"].isin(primeiros)] for nome, df in abas.items()}

    relatorio = service.importar(_xlsx(abas))

    assert relatorio.contagens["clientes"] == 10
    assert any("clientes" in aviso for aviso in relatorio.avisos)
