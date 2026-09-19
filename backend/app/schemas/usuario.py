from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_completo: str
    usuario: str


class UsuarioResponse(UsuarioResumo):
    criado_em: datetime
