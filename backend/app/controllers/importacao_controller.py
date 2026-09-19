from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_importacao_service, get_usuario_atual
from app.models import Usuario
from app.schemas.importacao import RelatorioImportacaoResponse
from app.services.importacao_service import ImportacaoService, RelatorioImportacao

router = APIRouter(tags=["importacao"])


@router.post("/importacao", response_model=RelatorioImportacaoResponse)
def importar(
    arquivo: UploadFile = File(..., description="Planilha INOVAAPPS (.xlsx)"),
    usuario: Usuario = Depends(get_usuario_atual),
    importacao: ImportacaoService = Depends(get_importacao_service),
) -> RelatorioImportacao:
    return importacao.importar(arquivo.file.read())
