from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    correo: str = Field(index=True, unique=True)
    contrasena_hash: str
    es_admin: bool = False
    activo: bool = True
    creado_en: datetime = Field(default_factory=utc_now)


class Proyecto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    descripcion: str | None = None
    creado_por_id: int = Field(foreign_key="usuario.id", index=True)
    fase_actual: int = 1
    estado: str = "activo"  # activo | concluido
    creado_en: datetime = Field(default_factory=utc_now)
    concluido_en: datetime | None = None


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
    fase: int = 1
    # votacion -> el equipo acuerda los puntos; pendiente -> se puede trabajar; completada
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


class VotoPuntos(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    actividad_id: int = Field(foreign_key="actividad.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    puntos: float = Field(ge=0)
    creado_en: datetime = Field(default_factory=utc_now)


class EvaluacionPares(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id", index=True)
    fase: int = 1
    evaluador_id: int = Field(foreign_key="usuario.id", index=True)
    evaluado_id: int = Field(foreign_key="usuario.id", index=True)
    comunicacion: int = Field(default=3, ge=1, le=5)
    calidad: int = Field(default=3, ge=1, le=5)
    compromiso: int = Field(default=3, ge=1, le=5)
    puntuacion: float = Field(ge=0)
    confirma_aporte: bool = True
    comentario: str | None = None
    creado_en: datetime = Field(default_factory=utc_now)


class Contribucion(SQLModel, table=True):
    """Puntos validados de una actividad, guardados al cerrar su fase."""

    id: int | None = Field(default=None, primary_key=True)
    actividad_id: int = Field(foreign_key="actividad.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    puntos_validados: float = Field(default=0, ge=0)
    creado_en: datetime = Field(default_factory=utc_now)


class FirmaDeclaracion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proyecto_id: int = Field(foreign_key="proyecto.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    puntos_validados: float = 0
    porcentaje: float = 0
    creado_en: datetime = Field(default_factory=utc_now)


class Configuracion(SQLModel, table=True):
    """Parámetros globales que define el administrador (una sola fila, id=1)."""

    id: int | None = Field(default=None, primary_key=True)
    porcentaje_minimo: float = Field(default=70, ge=0, le=100)
    dias_inactividad: int = Field(default=5, ge=1)
    actualizado_en: datetime = Field(default_factory=utc_now)
