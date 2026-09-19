from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração da aplicação, lida de variáveis de ambiente / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./holder.db"
    jwt_secret: str = "trocar-em-producao-use-uma-chave-longa-e-aleatoria"
    jwt_expira_minutos: int = 480
    cors_origens: str = "http://localhost:8501,http://localhost:5173"
    capacidade_fila: int = 10
    limiar_critico: float = 0.55
    limiar_atencao: float = 0.30
    limiar_monitorar: float = 0.15
    persistencia_min_meses: int = 2
    caminho_xlsx: str = "../INOVAAPPS_base_de_dados.xlsx"

    @property
    def lista_cors(self) -> list[str]:
        return [origem.strip() for origem in self.cors_origens.split(",") if origem.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
