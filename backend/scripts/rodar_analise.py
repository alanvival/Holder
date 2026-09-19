"""Roda a análise de produção sobre os dados já importados.

Uso (a partir de backend/):  python -m scripts.rodar_analise [AAAA-MM]
"""

import sys
from datetime import date

from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, criar_engine
from app.services.fabrica import criar_analise_service


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    mes = None
    if argv:
        try:
            ano, mes_num = argv[0].split("-")
            mes = date(int(ano), int(mes_num), 1)
        except (ValueError, TypeError):
            print("Uso: python -m scripts.rodar_analise [AAAA-MM]", file=sys.stderr)
            return 2
    settings = get_settings()
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            execucao = criar_analise_service(session, settings).executar(mes)
            print(
                f"Análise concluída: mês {execucao.mes_referencia}, "
                f"{execucao.qtd_clientes_avaliados} clientes avaliados, "
                f"{execucao.qtd_na_fila} na fila."
            )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
