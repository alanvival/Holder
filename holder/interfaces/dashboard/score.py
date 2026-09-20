"""
Aba 3 — Score de Risco (preditivo).

Lê do histórico já salvo (`fScoreRisco`, mês mais recente) em vez de
recalcular na hora: é mais rápido e é exatamente o valor persistido pelo job
de treino, não um recorte à parte.
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from holder.dominio.risco import faixas
from holder.infra.persistencia import historico_score, log_treinos

from .estilo import CORES_FAIXA, modulo_header

COMANDO_DE_TREINO = "python -m holder.aplicacao.treino"

NOMES_DE_SINAL = {
    'atraso_pagamento': 'Atraso de pagamento',
    'chamados_criticos': 'Chamados críticos',
    'sla_cumprido': 'SLA cumprido',
    'uso_plataforma': 'Uso da plataforma',
    'tempo_resolucao': 'Tempo de resolução',
    'reclamacoes': 'Reclamações',
    'nps': 'NPS',
}

# Sinais agrupados como "precoce" na explicabilidade — só rótulo de
# apresentação, não um segundo cálculo.
SINAIS_PRECOCE = ('atraso_pagamento', 'chamados_criticos')


@st.cache_data(ttl=600)
def _carregar_score_atual(ativos_ids: frozenset) -> list[dict]:
    hist = historico_score.carregar_historico()
    if hist.empty:
        return []
    mes_mais_recente = hist["mes_ref"].max()
    linhas = hist[(hist["mes_ref"] == mes_mais_recente) & (hist["cliente_id"].isin(ativos_ids))]
    resultados = [
        {
            "cliente_id": r["cliente_id"], "mes_ref": r["mes_ref"],
            "score_precoce": r["score_precoce"], "score_confirmado": r["score_confirmado"],
            "risco_percentual": r["risco_percentual"], "faixa": r["faixa"],
            "sinais_detalhados": json.loads(r["sinais_detalhados"]),
        }
        for _, r in linhas.iterrows()
    ]
    resultados.sort(key=lambda r: r["risco_percentual"], reverse=True)
    return resultados


@st.cache_data(ttl=600)
def _carregar_historico() -> pd.DataFrame:
    return historico_score.carregar_historico()


def _tendencia(row) -> str:
    if pd.isna(row.get('risco_anterior')):
        return '—'
    delta = row['risco_percentual'] - row['risco_anterior']
    if delta > 3:
        return '↑ subindo'
    if delta < -3:
        return '↓ caindo'
    return '→ estável'


def _enriquecer(resultados, df_cli, df_historico):
    df_score = pd.DataFrame(resultados)
    df_score = df_score.merge(df_cli[['cliente_id', 'plano', 'porte', 'segmento']], on='cliente_id', how='left')

    mes_atual = df_score['mes_ref'].iloc[0]
    mes_anterior = (pd.Period(mes_atual, freq='M') - 1).strftime('%Y-%m')

    # Tendência: compara o risco% deste mês com o do mês anterior salvo no
    # histórico — alimenta a seta subiu/caiu/estável e o alerta de "cruzou
    # de faixa".
    anterior = df_historico[df_historico['mes_ref'] == mes_anterior][['cliente_id', 'risco_percentual', 'faixa']]
    anterior = anterior.rename(columns={'risco_percentual': 'risco_anterior', 'faixa': 'faixa_anterior'})
    df_score = df_score.merge(anterior, on='cliente_id', how='left')

    df_score['tendencia'] = df_score.apply(_tendencia, axis=1)
    df_score['cruzou_faixa'] = df_score.apply(
        lambda r: bool(pd.notna(r.get('faixa_anterior')) and r['faixa_anterior'] != r['faixa']), axis=1
    )
    df_score['estagio_predominante'] = df_score.apply(
        lambda r: 'Precoce' if r['score_precoce'] > r['score_confirmado'] else 'Confirmado', axis=1
    )
    return df_score, mes_atual


def _lista_ranqueada(df_filtrado) -> None:
    """Linha "hero": o score é o elemento maior e mais destacado (colorido
    pela faixa), com uma barrinha curta de indicador rápido e a faixa como
    badge no fim — nome, estágio e tendência não cabem no rótulo colapsado
    de um expander, então essa parte vai em HTML acima dele."""
    st.subheader(f"{len(df_filtrado)} cliente(s) — ordenado por risco decrescente")
    for _, r in df_filtrado.iterrows():
        cor = CORES_FAIXA[r['faixa']]
        alerta = " · cruzou de faixa" if r['cruzou_faixa'] else ""
        largura_barra = max(4, min(100, r['risco_percentual']))

        col_score, col_bar, col_meta, col_badge = st.columns([1, 1.3, 3, 1.4])
        with col_score:
            st.markdown(
                f"<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:700;"
                f"font-size:1.75rem;line-height:1;color:{cor};'>{r['risco_percentual']:.0f}%</div>",
                unsafe_allow_html=True,
            )
        with col_bar:
            st.markdown(
                f"<div style='margin-top:12px;width:88px;height:8px;border-radius:4px;"
                f"background:rgba(0,10,30,0.08);overflow:hidden;'>"
                f"<div style='width:{largura_barra}%;height:100%;background:{cor};'></div></div>",
                unsafe_allow_html=True,
            )
        with col_meta:
            st.markdown(
                f"<div style='margin-top:2px;font-family:\"Montserrat\",sans-serif;'>"
                f"<b>{r['cliente_id']}</b><br>"
                f"<span style='font-size:0.8rem;color:rgba(0,10,30,0.6);'>"
                f"[{r['estagio_predominante']}] · {r['tendencia']}{alerta}</span></div>",
                unsafe_allow_html=True,
            )
        with col_badge:
            st.markdown(
                f"<div style='margin-top:6px;display:inline-block;background:{cor}33;"
                f"border:1px solid {cor};color:#000A1E;border-radius:12px;padding:4px 12px;"
                f"font-family:\"Montserrat\",sans-serif;font-size:0.78rem;font-weight:600;'>"
                f"{r['faixa']}</div>",
                unsafe_allow_html=True,
            )

        with st.expander("Ver detalhes e sinais"):
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.write(f"**Plano/Porte/Segmento:** {r['plano']} · {r['porte']} · {r['segmento']}")
                st.write(f"**Tendência (vs. mês anterior):** {r['tendencia']}")
            with col_b:
                sinais = r['sinais_detalhados']
                contrib = {NOMES_DE_SINAL.get(k, k): v.get('contribuicao', 0) or 0 for k, v in sinais.items()}
                fig = go.Figure(go.Bar(
                    x=list(contrib.values()), y=list(contrib.keys()), orientation='h',
                    marker_color=['#0156FC' if k in SINAIS_PRECOCE else '#1D1DDB' for k in sinais.keys()],
                ))
                fig.update_layout(
                    height=220, margin=dict(l=0, r=10, t=10, b=10),
                    xaxis=dict(range=[0, 100], title='contribuição pro score (0-100)'),
                    template='plotly_white',
                )
                st.plotly_chart(fig, use_container_width=True)
                if sinais.get('nps', {}).get('classificacao_recente'):
                    st.caption(f"Último NPS: {sinais['nps']['classificacao_recente']}")
                baseline_atraso = sinais.get('atraso_pagamento', {}).get('baseline_pessoal')
                if baseline_atraso is not None:
                    st.caption(
                        f"Atraso atual: {sinais['atraso_pagamento']['valor_atual']} dias "
                        f"(baseline pessoal: {baseline_atraso:.1f})"
                    )

        st.markdown(
            "<div style='height:10px;border-bottom:1px solid rgba(0,10,30,0.06);margin-bottom:10px;'></div>",
            unsafe_allow_html=True,
        )


def _cards_por_faixa(df_filtrado) -> None:
    for col, faixa in zip(st.columns(4), faixas.NOMES[::-1]):
        with col:
            subset = df_filtrado[df_filtrado['faixa'] == faixa]
            st.markdown(f"##### {faixa} ({len(subset)})")
            for _, r in subset.sort_values('risco_percentual', ascending=False).iterrows():
                st.markdown(
                    f"<div style='background:{CORES_FAIXA[faixa]}22;border-left:4px solid {CORES_FAIXA[faixa]};"
                    f"border-radius:8px;padding:8px 10px;margin-bottom:6px;'>"
                    f"<b>{r['cliente_id']}</b> — {r['risco_percentual']:.0f}%<br>"
                    f"<span style='font-size:12px;color:#555;'>{r['tendencia']}</span></div>",
                    unsafe_allow_html=True,
                )


def _linha_do_tempo(df_filtrado, df_score, df_historico) -> None:
    cliente = st.selectbox(
        "Cliente:",
        sorted(df_filtrado['cliente_id'].unique()) or sorted(df_score['cliente_id'].unique()),
    )
    hist_cliente = df_historico[df_historico['cliente_id'] == cliente].sort_values('mes_ref')
    if hist_cliente.empty:
        st.info("Sem histórico salvo pra esse cliente ainda.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_cliente['mes_ref'], y=hist_cliente['risco_percentual'],
        mode='lines+markers+text', text=hist_cliente['risco_percentual'].round(0),
        textposition='top center', line=dict(width=3, color='#0156FC'), name='Risco %',
    ))
    for lo, hi, nome in faixas.FAIXAS:
        fig.add_hrect(y0=lo, y1=min(hi, 100), fillcolor=CORES_FAIXA[nome], opacity=0.15, line_width=0)
    fig.update_layout(
        xaxis_title='Mês', yaxis_title='Risco de cancelamento (%)', yaxis=dict(range=[0, 100]),
        template='plotly_white', hovermode='x unified',
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Faixas de fundo: verde = Saudável, amarelo claro = Atenção, laranja = Em risco, vermelho = Crítico.")


def _metodologia() -> None:
    st.markdown("---")
    with st.expander("Sobre este score (metodologia)"):
        df_log = log_treinos.carregar()
        if not df_log.empty:
            ultimo = df_log.iloc[0]
            validacao = (
                f"**AUC = {ultimo['auc']:.3f}** · **Brier = {ultimo['brier']:.3f}** "
                f"(validação cruzada 5-fold, treinado em "
                f"{pd.to_datetime(ultimo['treinado_em']).strftime('%d/%m/%Y')}, "
                f"{int(ultimo['n_amostras'])} amostras)."
            )
        else:
            validacao = f"Sem log de treino ainda — rode `{COMANDO_DE_TREINO}`."

        st.markdown(f"""
        **Regressão logística treinada e validada** contra os cancelamentos reais da base —
        não é um score de pesos escolhidos à mão. {validacao}

        - **Alvo do treino:** cada mês de cada cliente cancelado vira `y=1` só se estiver dentro
          dos 3 meses imediatamente antes do cancelamento (meses mais antigos são excluídos do
          treino, não viram `y=0`) — o modelo aprende "esse mês parece pré-cancelamento", não
          "esse cliente é do tipo que cancela".
        - **Variáveis:** SLA cumprido, tempo de resolução, reclamações, uso da plataforma,
          atraso de pagamento, chamados críticos e NPS mais recente conhecido.
        - **Explicabilidade:** cada sinal no detalhe do cliente mostra coeficiente × desvio —
          "precoce"/"confirmado" é só rótulo de apresentação (atraso/críticos vs. os demais),
          não um segundo cálculo paralelo.

        Faixas: Saudável (0–29%) · Atenção (30–54%) · Em risco (55–74%) · Crítico (75–100%).
        Backtest retroativo nos 22 clientes já cancelados: ver `testes/test_modelo_risco.py`.
        """)


def renderizar(df_cli, df_sit) -> None:
    ativos_ids = frozenset(df_sit[df_sit["situacao"] == "Ativo"]["cliente_id"])
    resultados = _carregar_score_atual(ativos_ids)
    df_historico = _carregar_historico()

    with st.container(border=True):
        modulo_header(
            "Score de Risco (Preditivo)",
            "Regressão logística treinada e validada contra os cancelamentos reais, atualizada mensalmente.",
        )
        if not resultados:
            st.warning(f"Sem score calculado ainda. Rode `{COMANDO_DE_TREINO}` no terminal pra popular o histórico.")
            return

        df_score, mes_atual = _enriquecer(resultados, df_cli, df_historico)
        st.caption(
            f"Score calculado com base no mês mais recente disponível: **{mes_atual}** · "
            f"{len(df_score)} clientes ativos avaliados."
        )

        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            faixas_sel = st.multiselect("Faixa de risco", faixas.NOMES[::-1], default=faixas.NOMES[::-1])
        with col_f2:
            planos_sel = st.multiselect("Plano", sorted(df_score['plano'].dropna().unique()), default=None)
        with col_f3:
            segmentos_sel = st.multiselect("Segmento", sorted(df_score['segmento'].dropna().unique()), default=None)
        with col_f4:
            estagio_sel = st.multiselect("Estágio predominante", ['Precoce', 'Confirmado'], default=None)

        df_filtrado = df_score[df_score['faixa'].isin(faixas_sel)]
        if planos_sel:
            df_filtrado = df_filtrado[df_filtrado['plano'].isin(planos_sel)]
        if segmentos_sel:
            df_filtrado = df_filtrado[df_filtrado['segmento'].isin(segmentos_sel)]
        if estagio_sel:
            df_filtrado = df_filtrado[df_filtrado['estagio_predominante'].isin(estagio_sel)]

        modo = st.radio(
            "Modo de visualização",
            ["Lista ranqueada", "Cards por faixa", "Linha do tempo (cliente)"],
            horizontal=True,
        )

        if modo == "Lista ranqueada":
            _lista_ranqueada(df_filtrado)
        elif modo == "Cards por faixa":
            _cards_por_faixa(df_filtrado)
        else:
            _linha_do_tempo(df_filtrado, df_score, df_historico)

        _metodologia()
