"""
Identidade visual do dashboard.

Fonte da verdade dos tokens: `docs/design-tokens.md`. As fontes (Space
Grotesk nos títulos, Montserrat no corpo) e as cores vêm do tema nativo do
Streamlit (`.streamlit/config.toml`) — isso é necessário porque
`st.dataframe` renderiza a grade em canvas (glide-data-grid), não HTML,
então CSS de página não alcança o texto das células e cabeçalhos; só a
fonte do tema nativo se propaga até lá.

O CSS abaixo cobre só o que o tema não tem: raio de borda de cards/tabelas
e formato de pílula nos botões.
"""
from __future__ import annotations

import streamlit as st

# Cor de cada faixa do score de risco. Única fonte de "o que essa cor
# significa" em qualquer tabela do dashboard — antes cada seção inventava
# sua própria escala (havia um gradiente contínuo `cmap='Reds'` sem
# correspondência com as faixas do resto do app), e este dicionário estava
# declarado duas vezes no mesmo arquivo.
CORES_FAIXA = {
    "Saudável": "#A9DFBF",
    "Atenção": "#F9E79F",
    "Em risco": "#F5B041",
    "Crítico": "#E74C3C",
}

# Níveis do índice de alerta — azuis de marca, deliberadamente frios, pra
# não competir com a escala quente das faixas acima. São conceitos
# diferentes (ver CONTEXT.md) e quem lê a tela precisa perceber isso de
# olho, não só pelo rótulo.
CORES_ALERTA = {
    "Baixo": "#C7D3E8",
    "Médio": "#1D1DDB",
    "Alto": "#0000AA",
}

CSS = """
    <style>
    /* Toolbar de desenvolvimento do Streamlit (menu ⋮, "Deploy", barra de
       status "Running"/"Stop") — visível por padrão em qualquer app rodado
       com `streamlit run`, mas lê como "notebook em andamento", não produto
       pronto. Escondida pra demonstração; não afeta nenhum dado exibido. */
    #MainMenu, header[data-testid="stHeader"], div[data-testid="stToolbar"],
    div[data-testid="stDecoration"], div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    .stApp { margin-top: -3.5rem; }

    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        word-wrap: break-word !important;
        font-size: 1.7rem !important;
        line-height: 1.2 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 20px !important;
        overflow: hidden;
    }

    /* "Módulo" = cada seção do dashboard (Matriz, Monitor Individual, Score
       de Risco, Painel de Strikes) dentro do seu próprio st.container(border=True)
       — antes tudo ficava soltinho na mesma coluna, sem separação visual
       nenhuma entre uma tabela e a próxima. Padding generoso + espaço entre
       módulos, reaproveitando o raio de 20px que já existia aqui. */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        overflow: hidden;
        margin-bottom: 36px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {
        padding: 32px;
        gap: 0.9rem;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 50px !important;
    }
    </style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def modulo_header(titulo: str, subtitulo: str) -> None:
    st.markdown(f"""
        <div style="margin-bottom:14px;">
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.375rem;color:#000A1E;line-height:1.25;">{titulo}</div>
          <div style="font-family:'Montserrat',sans-serif;font-weight:400;font-size:0.875rem;color:rgba(0,10,30,0.55);margin-top:2px;">{subtitulo}</div>
        </div>
    """, unsafe_allow_html=True)


def cores_por_corte(serie, cortes):
    """Quatro baldes discretos com a paleta das faixas, em vez de gradiente
    contínuo — três cortes dividem a série em Saudável/Atenção/Em risco/
    Crítico."""
    c1, c2, c3 = cortes

    def cor_de(v):
        if v <= c1:
            return CORES_FAIXA["Saudável"]
        if v <= c2:
            return CORES_FAIXA["Atenção"]
        if v <= c3:
            return CORES_FAIXA["Em risco"]
        return CORES_FAIXA["Crítico"]

    return [f"background-color: {cor_de(v)}" for v in serie]
