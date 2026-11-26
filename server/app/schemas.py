from typing import Annotated, Literal

from pydantic import StringConstraints
from sqlmodel import Field, SQLModel

from app.models import Actividad, Avance, Participacion, Proyecto


Email = Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)]


class RegisterRequest(SQLModel):
    nombre: str = Field(min_length=1, max_length=120)
    correo: Email
    contrasena: str = Field(min_length=8, max_length=128)


class LoginRequest(SQLModel):
    correo: Email
    contrasena: str


class UsuarioPublic(SQLModel):
    id: int
    nombre: str
    correo: str
    es_admin: bool = False
    activo: bool = True


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class ProyectoCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str | None = None


class ProyectoPublic(SQLModel):
    id: int
    nombre: str
    descripcion: str | None
    creado_por_id: int
    fase_actual: int = 1
    estado: str = "activo"
    creado_en: str

    @classmethod
    def from_model(cls, proyecto: Proyecto) -> "ProyectoPublic":
        return cls(
            id=proyecto.id,
            nombre=proyecto.nombre,
            descripcion=proyecto.descripcion,
            creado_por_id=proyecto.creado_por_id,
            fase_actual=proyecto.fase_actual,
            estado=proyecto.estado,
            creado_en=proyecto.creado_en.isoformat(),
        )


class InvitacionCreate(SQLModel):
    correo: Email


class InvitacionResponse(SQLModel):
    id: int
    proyecto_id: int
    usuario_id: int
    rol: str
    estado: str
    creado_en: str
    nombre_proyecto: str

    @classmethod
    def from_model(cls, participacion: Participacion, nombre_proyecto: str) -> "InvitacionResponse":
        return cls(
            id=participacion.id,
            proyecto_id=participacion.proyecto_id,
            usuario_id=participacion.usuario_id,
            rol=participacion.rol,
            estado=participacion.estado,
            creado_en=participacion.creado_en.isoformat(),
            nombre_proyecto=nombre_proyecto,
        )


class IntegrantePublic(SQLModel):
    id: int
    nombre: str
    correo: str
    rol: str


class InvitacionDecision(SQLModel):
    respuesta: Literal["aceptar", "rechazar"]


class ProyectoListResponse(SQLModel):
    proyectos: list[ProyectoPublic]
    invitaciones_pendientes: list[InvitacionResponse]


class ActividadCreate(SQLModel):
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str | None = None
    puntos_acordados: float = Field(ge=0)
    responsable_id: int


class ActividadPublic(SQLModel):
    id: int
    proyecto_id: int
    responsable_id: int
    nombre: str
    descripcion: str | None
    puntos_acordados: float
    estado: str
    fase: int = 1
    votos_emitidos: int = 0
    votos_requeridos: int = 0
    mi_voto: float | None = None
    creado_en: str

    @classmethod
    def from_model(
        cls,
        actividad: Actividad,
        votos_emitidos: int = 0,
        votos_requeridos: int = 0,
        mi_voto: float | None = None,
    ) -> "ActividadPublic":
        return cls(
            id=actividad.id,
            proyecto_id=actividad.proyecto_id,
            responsable_id=actividad.responsable_id,
            nombre=actividad.nombre,
            descripcion=actividad.descripcion,
            puntos_acordados=actividad.puntos_acordados,
            estado=actividad.estado,
            fase=actividad.fase,
            votos_emitidos=votos_emitidos,
            votos_requeridos=votos_requeridos,
            mi_voto=mi_voto,
            creado_en=actividad.creado_en.isoformat(),
        )


class AvanceCreate(SQLModel):
    descripcion: str = Field(min_length=1, max_length=4000)
    url_evidencia: str | None = None


class AvanceDecision(SQLModel):
    estado: Literal["aprobado", "rechazado"]
    comentario: str | None = Field(default=None, max_length=1000)


class AvancePublic(SQLModel):
    id: int
    actividad_id: int
    usuario_id: int
    descripcion: str
    url_evidencia: str | None
    estado: str
    comentario_revision: str | None
    creado_en: str
    revisado_en: str | None

    @classmethod
    def from_model(cls, avance: Avance) -> "AvancePublic":
        return cls(
            id=avance.id,
            actividad_id=avance.actividad_id,
            usuario_id=avance.usuario_id,
            descripcion=avance.descripcion,
            url_evidencia=avance.url_evidencia,
            estado=avance.estado,
            comentario_revision=avance.comentario_revision,
            creado_en=avance.creado_en.isoformat(),
            revisado_en=avance.revisado_en.isoformat() if avance.revisado_en else None,
        )


# --- Iteración 2 -----------------------------------------------------------


class VotoCreate(SQLModel):
    puntos: float = Field(ge=0, le=1000)


class EvaluacionCreate(SQLModel):
    evaluado_id: int
    comunicacion: int = Field(ge=1, le=5)
    calidad: int = Field(ge=1, le=5)
    compromiso: int = Field(ge=1, le=5)
    confirma_aporte: bool = True
    comentario: str | None = Field(default=None, max_length=1000)


class EvaluacionPublic(SQLModel):
    id: int
    fase: int
    evaluador_id: int
    evaluado_id: int
    comunicacion: int
    calidad: int
    compromiso: int
    puntuacion: float
    confirma_aporte: bool
    comentario: str | None


class ContribucionIntegrante(SQLModel):
    usuario_id: int
    nombre: str
    rol: str
    puntos_aprobados: float
    puntos_validados: float
    porcentaje: float
    cumple: bool
    confirmaciones: int
    evaluaciones_recibidas: int
    evaluaciones_pendientes: int
    promedio_evaluacion: float | None


class ContribucionResponse(SQLModel):
    fase: int
    estado_proyecto: str
    porcentaje_minimo: float
    puntos_fase: float
    parte_justa: float
    integrantes: list[ContribucionIntegrante]
    mis_evaluaciones: list[EvaluacionPublic]
    checkin_abierto: bool = False
    aviso: str | None
    puede_cerrar: bool
    pendientes_cierre: list[str]


class DeclaracionIntegrante(SQLModel):
    usuario_id: int
    nombre: str
    rol: str
    puntos_validados: float
    porcentaje: float
    actividades: list[str]
    firmado: bool
    firmado_en: str | None


class DeclaracionResponse(SQLModel):
    proyecto_id: int
    nombre_proyecto: str
    concluido_en: str | None
    puntos_totales: float
    integrantes: list[DeclaracionIntegrante]
    puedo_firmar: bool
    motivo: str | None


class ConfiguracionPublic(SQLModel):
    porcentaje_minimo: float
    dias_inactividad: int


class ConfiguracionUpdate(SQLModel):
    porcentaje_minimo: float = Field(ge=0, le=100)
    dias_inactividad: int = Field(ge=1, le=365)


class UsuarioAdminUpdate(SQLModel):
    activo: bool | None = None
    es_admin: bool | None = None


class ReporteProyecto(SQLModel):
    id: int
    nombre: str
    lider: str
    estado: str
    fase_actual: int
    integrantes: int
    actividades: int
    actividades_completadas: int
    puntos_totales: float
    puntos_validados: float
    integrantes_bajo_minimo: int
    integrantes_inactivos: int


class ReporteResponse(SQLModel):
    usuarios: int
    usuarios_activos: int
    proyectos: int
    proyectos_concluidos: int
    porcentaje_minimo: float
    dias_inactividad: int
    detalle: list[ReporteProyecto]
