"""Importa a planilha para o banco.

Uso (a partir de backend/):  python -m scripts.importar_base [caminho.xlsx]
"""

import sys

from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, criar_engine
from app.services.fabrica import criar_importacao_service


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    settings = get_settings()
    caminho = argv[0] if argv else settings.caminho_xlsx
    engine = criar_engine(settings.database_url)
    Base.metadata.create_all(engine)
    try:
        with Session(engine, expire_on_commit=False) as session:
            relatorio = criar_importacao_service(session, settings).importar(caminho)
            print("Importação concluída:")
            for tabela, quantidade in relatorio.contagens.items():
                print(f"  {tabela}: {quantidade}")
            for aviso in relatorio.avisos:
                print(f"  AVISO: {aviso}")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
