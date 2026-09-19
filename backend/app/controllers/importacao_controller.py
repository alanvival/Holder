from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_analise_service, get_importacao_service, get_usuario_atual
from app.models import Usuario
from app.schemas.analise import ExecucaoResponse
from app.schemas.importacao import RelatorioImportacaoResponse
from app.services.analise_service import AnaliseService
from app.services.importacao_service import ImportacaoService

router = APIRouter(tags=["importacao"])


@router.post("/importacao", response_model=RelatorioImportacaoResponse)
def importar(
    arquivo: UploadFile = File(..., description="Planilha INOVAAPPS (.xlsx)"),
    usuario: Usuario = Depends(get_usuario_atual),
    importacao: ImportacaoService = Depends(get_importacao_service),
    analise: AnaliseService = Depends(get_analise_service),
) -> RelatorioImportacaoResponse:
    """Importa a planilha (substitui os dados de origem) e roda a análise de produção."""
    relatorio = importacao.importar(arquivo.file.read())
    execucao = analise.executar(usuario_id=usuario.id)
    return RelatorioImportacaoResponse(
        contagens=relatorio.contagens,
        avisos=relatorio.avisos,
        execucao=ExecucaoResponse.model_validate(execucao),
    )
