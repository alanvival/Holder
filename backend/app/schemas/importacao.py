from pydantic import BaseModel, ConfigDict

from app.schemas.analise import ExecucaoResponse


class RelatorioImportacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contagens: dict[str, int]
    avisos: list[str]
    execucao: ExecucaoResponse | None = None
