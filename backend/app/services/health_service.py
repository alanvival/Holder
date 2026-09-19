from app.repositories.health_repository import HealthRepository


class HealthService:
    """Informa se a API está no ar e se o banco responde."""

    def __init__(self, repo: HealthRepository) -> None:
        self._repo = repo

    def status(self) -> dict[str, str]:
        return {"status": "ok", "banco": "ok" if self._repo.ping() else "erro"}
