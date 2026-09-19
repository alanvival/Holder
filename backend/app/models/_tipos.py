from enum import Enum

from sqlalchemy import Enum as SAEnum


def coluna_enum(enum_cls: type[Enum]) -> SAEnum:
    """Enum guardado como VARCHAR(20) com o nome do membro (portável SQLite/SQL Server)."""
    return SAEnum(enum_cls, native_enum=False, length=20, validate_strings=True)
