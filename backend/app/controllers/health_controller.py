from fastapi import APIRouter, Depends

from app.dependencies import get_health_service
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(service: HealthService = Depends(get_health_service)) -> dict[str, str]:
    return service.status()
