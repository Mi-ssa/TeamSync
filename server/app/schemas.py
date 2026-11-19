from typing import Literal

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
    creado_en: str

    @classmethod
    def from_model(cls, proyecto: Proyecto) -> "ProyectoPublic":
        return cls(
            id=proyecto.id,
            nombre=proyecto.nombre,
            descripcion=proyecto.descripcion,
            creado_por_id=proyecto.creado_por_id,
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
    creado_en: str

    @classmethod
    def from_model(cls, actividad: Actividad) -> "ActividadPublic":
        return cls(
            id=actividad.id,
            proyecto_id=actividad.proyecto_id,
            responsable_id=actividad.responsable_id,
            nombre=actividad.nombre,
            descripcion=actividad.descripcion,
            puntos_acordados=actividad.puntos_acordados,
            estado=actividad.estado,
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
