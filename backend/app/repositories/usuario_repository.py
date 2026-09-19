from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Usuario


class UsuarioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        return self._session.get(Usuario, usuario_id)

    def obter_por_usuario(self, usuario: str) -> Usuario | None:
        return self._session.scalar(select(Usuario).where(Usuario.usuario == usuario))

    def adicionar(self, usuario: Usuario) -> Usuario:
        self._session.add(usuario)
        self._session.commit()
        self._session.refresh(usuario)
        return usuario

    def salvar(self, usuario: Usuario) -> Usuario:
        self._session.commit()
        return usuario
