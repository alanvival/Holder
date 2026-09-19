from pydantic import BaseModel, ConfigDict


class RelatorioImportacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contagens: dict[str, int]
    avisos: list[str]
