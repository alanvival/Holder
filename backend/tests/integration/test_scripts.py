import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from scripts import importar_base, rodar_analise


@pytest.fixture
def banco_arquivo(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'script.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def test_script_importar_base(banco_arquivo, caminho_xlsx, capsys):
    assert importar_base.main([str(caminho_xlsx)]) == 0

    engine = create_engine(banco_arquivo)
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT COUNT(*) FROM clientes")).scalar() == 80
    engine.dispose()
    assert "clientes: 80" in capsys.readouterr().out


def test_scripts_importar_e_rodar_analise(banco_arquivo, caminho_xlsx, capsys):
    assert importar_base.main([str(caminho_xlsx)]) == 0
    assert rodar_analise.main([]) == 0

    engine = create_engine(banco_arquivo)
    with engine.connect() as conexao:
        execucoes = conexao.execute(text("SELECT COUNT(*) FROM execucoes_analise")).scalar()
    engine.dispose()
    assert execucoes == 2
    saida = capsys.readouterr().out
    assert "Análise concluída" in saida
