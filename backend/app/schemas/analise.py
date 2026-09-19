from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import TipoExecucao


class ExecucaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoExecucao
    mes_referencia: date
    versao_modelo: str
    executado_em: datetime
    qtd_clientes_avaliados: int
    qtd_na_fila: int
