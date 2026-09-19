from datetime import date

from pydantic import BaseModel


class VariavelMetrica(BaseModel):
    codigo: str
    rotulo: str


class PontoMensal(BaseModel):
    mes_ref: date
    valor: float
