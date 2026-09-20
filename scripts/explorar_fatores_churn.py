"""
Exploração: o que mais difere entre clientes ativos e cancelados.

Script de apoio, não parte da aplicação — imprime o ranking e abre um
gráfico no navegador. Útil para defender a escolha dos pesos do índice de
alerta, já que mostra de onde eles vêm.

    python scripts/explorar_fatores_churn.py

Este arquivo era `churn.py`, na raiz do repo, e tinha **fórmula própria**:
calculava a influência por correlação de Pearson contra um alvo binário,
enquanto o domínio calculava por contraste entre as médias dos dois grupos.
Duas respostas diferentes para a mesma pergunta, em dois arquivos, nenhum
importando o outro. A fórmula do domínio venceu (é a que alimenta os pesos e
a que já estava validada), e aqui sobrou só a apresentação.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px

from holder.dominio.churn import analisar_fatores_churn

CORES = {
    "Sobe antes do cancelamento": "#E74C3C",
    "Cai antes do cancelamento": "#2B5B84",
}


def main() -> None:
    analise = analisar_fatores_churn()
    ranking = analise["ranking_por_maior_diferenca"]

    df = pd.DataFrame(ranking)
    df["Direção"] = df["diferenca_percentual"].apply(
        lambda x: "Sobe antes do cancelamento" if x > 0 else "Cai antes do cancelamento"
    )

    print("\n" + "=" * 80)
    print("RAIO-X: COMPORTAMENTO MÉDIO (ATIVOS VS CANCELADOS)")
    print("=" * 80)
    print(analise["universo"])
    pd.options.display.float_format = "{:.2f}".format
    print(
        df[["rotulo", "valor_clientes_ativos", "valor_clientes_cancelados", "diferenca_percentual"]]
        .rename(columns={
            "rotulo": "Métrica",
            "valor_clientes_ativos": "Média dos Ativos",
            "valor_clientes_cancelados": "Média dos Cancelados",
            "diferenca_percentual": "Variação (%)",
        })
        .to_string(index=False)
    )
    print("=" * 80)
    print(analise["nota"])
    print()

    # Ordem crescente pelo valor com sinal, pro gráfico ficar simétrico em
    # torno do zero (quem sobe pra um lado, quem cai pro outro).
    df = df.sort_values(by="diferenca_percentual")

    fig = px.bar(
        df,
        x="diferenca_percentual",
        y="rotulo",
        color="Direção",
        color_discrete_map=CORES,
        title="O que mais difere entre quem cancelou e quem ficou",
    )
    fig.update_layout(
        xaxis_title="← Menor entre cancelados | diferença % | Maior entre cancelados →",
        yaxis_title="",
        template="plotly_white",
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.add_vline(x=0, line_width=2, line_color="black")
    fig.show()


if __name__ == "__main__":
    main()
