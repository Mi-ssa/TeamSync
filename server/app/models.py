from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    correo: str = Field(index=True, unique=True)
    contrasena_hash: str
    creado_en: datetime = Field(default_factory=utc_now)


class Proyecto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    descripcion: str | None = None
    creado_por_id: int = Field(foreign_key="usuario.id", index=True)
    creado_en: datetime = Field(default_factory=utc_now)


class Participacion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    rol: str = "integrante"
    estado: str = "pendiente"
    creado_en: datetime = Field(default_factory=utc_now)
    respondido_en: datetime | None = None


class Actividad(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id", index=True)
    responsable_id: int = Field(foreign_key="usuario.id", index=True)
    nombre: str
    descripcion: str | None = None
    puntos_acordados: float = Field(ge=0)
    estado: str = "pendiente"
    creado_en: datetime = Field(default_factory=utc_now)


class Avance(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actividad_id: int = Field(foreign_key="actividad.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    descripcion: str
    url_evidencia: str | None = None
    estado: str = "pendiente"
    comentario_revision: str | None = None
    creado_en: datetime = Field(default_factory=utc_now)
    revisado_en: datetime | None = None


class EvaluacionPares(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id", index=True)
    evaluador_id: int = Field(foreign_key="usuario.id", index=True)
    evaluado_id: int = Field(foreign_key="usuario.id", index=True)
    puntuacion: float = Field(ge=0)
    comentario: str | None = None
    creado_en: datetime = Field(default_factory=utc_now)


class Contribucion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actividad_id: int = Field(foreign_key="actividad.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    puntos_validados: float = Field(default=0, ge=0)
    creado_en: datetime = Field(default_factory=utc_now)
