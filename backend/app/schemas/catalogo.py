from pydantic import BaseModel, ConfigDict

from app.core.enums import Dimensao, Responsavel, SentidoPiora, TipoRegra


class SinalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    dimensao: Dimensao
    variavel: str
    tipo_regra: TipoRegra
    sentido_piora: SentidoPiora
    limiar: float
    metrica: str
    persistencia_min_meses: int
    peso: float
    lift: float | None
    cobertura_cancelados: float | None
    taxa_falso_alarme: float | None
    antecedencia_media_meses: float | None
    ativo: bool


class AcaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    titulo: str
    descricao: str
    dimensao_gatilho: Dimensao | None
    responsavel_sugerido: Responsavel
    prazo_dias: int
    ordem: int
