"""
Persistência do modelo treinado (pickle).

Artefato gerado, não código-fonte: fica fora do versionamento e se recria
rodando o treino.
"""
from __future__ import annotations

import pickle
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[3] / "modelo_risco.pkl"

COMANDO_DE_TREINO = "python -m holder.aplicacao.treino"


def existe() -> bool:
    return ARQUIVO.exists()


def salvar(modelo, scaler, mediana_features) -> None:
    with open(ARQUIVO, "wb") as f:
        pickle.dump({"modelo": modelo, "scaler": scaler, "mediana_features": mediana_features}, f)


def carregar():
    """Carregar é só carregar. Antes, se o arquivo não existisse, a função
    equivalente treinava o modelo, gravava o pickle e inseria uma linha no
    log de treinos — minutos de CPU e escrita em banco escondidos atrás de
    um nome que promete leitura."""
    if not existe():
        raise FileNotFoundError(
            f"Modelo não treinado: {ARQUIVO.name} não existe. "
            f"Rode `{COMANDO_DE_TREINO}` pra treinar, salvar e popular o histórico."
        )
    with open(ARQUIVO, "rb") as f:
        d = pickle.load(f)
    return d["modelo"], d["scaler"], d["mediana_features"]
