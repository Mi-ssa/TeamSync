from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth import CurrentUser, SessionDep
from app.models import Actividad, Participacion, Proyecto, Usuario
from app.schemas import (
    ActividadCreate,
    ActividadPublic,
    IntegrantePublic,
    InvitacionCreate,
    InvitacionDecision,
    InvitacionResponse,
    ProyectoCreate,
    ProyectoListResponse,
    ProyectoPublic,
)


router = APIRouter(tags=["Proyectos e invitaciones"])


def get_accepted_participation(session: SessionDep, proyecto_id: int, usuario_id: int) -> Participacion:
    participacion = session.exec(
        select(Participacion).where(
            Participacion.proyecto_id == proyecto_id,
            Participacion.usuario_id == usuario_id,
            Participacion.estado == "aceptada",
        )
    ).first()
    if participacion is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a este proyecto")
    return participacion


@router.post("/proyectos", response_model=ProyectoPublic, status_code=status.HTTP_201_CREATED)
def crear_proyecto(payload: ProyectoCreate, usuario: CurrentUser, session: SessionDep) -> ProyectoPublic:
    proyecto = Proyecto(
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion,
        creado_por_id=usuario.id,
    )
    session.add(proyecto)
    session.flush()
    session.add(
        Participacion(
            proyecto_id=proyecto.id,
            usuario_id=usuario.id,
            rol="lider",
            estado="aceptada",
            respondido_en=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.refresh(proyecto)
    return ProyectoPublic.from_model(proyecto)


@router.get("/proyectos", response_model=ProyectoListResponse)
def listar_proyectos(usuario: CurrentUser, session: SessionDep) -> ProyectoListResponse:
    participaciones = session.exec(
        select(Participacion).where(Participacion.usuario_id == usuario.id)
    ).all()
    proyectos: list[ProyectoPublic] = []
    invitaciones: list[InvitacionResponse] = []
    for participacion in participaciones:
        proyecto = session.get(Proyecto, participacion.proyecto_id)
        if proyecto is None:
            continue
        if participacion.estado == "aceptada":
            proyectos.append(ProyectoPublic.from_model(proyecto))
        elif participacion.estado == "pendiente":
            invitaciones.append(InvitacionResponse.from_model(participacion, proyecto.nombre))
    return ProyectoListResponse(proyectos=proyectos, invitaciones_pendientes=invitaciones)


@router.post(
    "/proyectos/{proyecto_id}/invitaciones",
    response_model=InvitacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def invitar_integrante(
    proyecto_id: int, payload: InvitacionCreate, usuario: CurrentUser, session: SessionDep
) -> InvitacionResponse:
    proyecto = session.get(Proyecto, proyecto_id)
    if proyecto is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    lider = get_accepted_participation(session, proyecto_id, usuario.id)
    if lider.rol != "lider":
        raise HTTPException(status_code=403, detail="Solo el líder puede invitar integrantes")

    correo = str(payload.correo).strip().lower()
    invitado = session.exec(select(Usuario).where(Usuario.correo == correo)).first()
    if invitado is None:
        raise HTTPException(status_code=404, detail="No existe un usuario registrado con ese correo")
    if invitado.id == usuario.id:
        raise HTTPException(status_code=409, detail="No puedes invitarte a tu propio proyecto")
    existente = session.exec(
        select(Participacion).where(
            Participacion.proyecto_id == proyecto_id,
            Participacion.usuario_id == invitado.id,
        )
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="El usuario ya tiene una invitación o participación")

    participacion = Participacion(proyecto_id=proyecto_id, usuario_id=invitado.id)
    session.add(participacion)
    session.commit()
    session.refresh(participacion)
    return InvitacionResponse.from_model(participacion, proyecto.nombre)


@router.post("/invitaciones/{invitacion_id}/responder", response_model=InvitacionResponse)
def responder_invitacion(
    invitacion_id: int, payload: InvitacionDecision, usuario: CurrentUser, session: SessionDep
) -> InvitacionResponse:
    participacion = session.get(Participacion, invitacion_id)
    if participacion is None or participacion.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    if participacion.estado != "pendiente":
        raise HTTPException(status_code=409, detail="La invitación ya fue respondida")
    proyecto = session.get(Proyecto, participacion.proyecto_id)
    if proyecto is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    participacion.estado = "aceptada" if payload.respuesta == "aceptar" else "rechazada"
    participacion.respondido_en = datetime.now(timezone.utc)
    session.add(participacion)
    session.commit()
    session.refresh(participacion)
    return InvitacionResponse.from_model(participacion, proyecto.nombre)


@router.get("/proyectos/{proyecto_id}", response_model=ProyectoPublic)
def obtener_proyecto(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> ProyectoPublic:
    proyecto = session.get(Proyecto, proyecto_id)
    if proyecto is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    get_accepted_participation(session, proyecto_id, usuario.id)
    return ProyectoPublic.from_model(proyecto)


@router.get("/proyectos/{proyecto_id}/integrantes", response_model=list[IntegrantePublic])
def listar_integrantes(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> list[IntegrantePublic]:
    if session.get(Proyecto, proyecto_id) is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    get_accepted_participation(session, proyecto_id, usuario.id)
    participaciones = session.exec(
        select(Participacion).where(
            Participacion.proyecto_id == proyecto_id,
            Participacion.estado == "aceptada",
        )
    ).all()
    integrantes: list[IntegrantePublic] = []
    for participacion in participaciones:
        integrante = session.get(Usuario, participacion.usuario_id)
        if integrante is not None:
            integrantes.append(
                IntegrantePublic(
                    id=integrante.id,
                    nombre=integrante.nombre,
                    correo=integrante.correo,
                    rol=participacion.rol,
                )
            )
    return integrantes


@router.post(
    "/proyectos/{proyecto_id}/actividades",
    response_model=ActividadPublic,
    status_code=status.HTTP_201_CREATED,
)
def crear_actividad(
    proyecto_id: int, payload: ActividadCreate, usuario: CurrentUser, session: SessionDep
) -> ActividadPublic:
    if session.get(Proyecto, proyecto_id) is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    lider = get_accepted_participation(session, proyecto_id, usuario.id)
    if lider.rol != "lider":
        raise HTTPException(status_code=403, detail="Solo el líder puede crear actividades")
    responsable = session.exec(
        select(Participacion).where(
            Participacion.proyecto_id == proyecto_id,
            Participacion.usuario_id == payload.responsable_id,
            Participacion.estado == "aceptada",
        )
    ).first()
    if responsable is None:
        raise HTTPException(status_code=400, detail="El responsable debe ser integrante aceptado del proyecto")

    actividad = Actividad(
        proyecto_id=proyecto_id,
        responsable_id=payload.responsable_id,
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion,
        puntos_acordados=payload.puntos_acordados,
    )
    session.add(actividad)
    session.commit()
    session.refresh(actividad)
    return ActividadPublic.from_model(actividad)


@router.get("/proyectos/{proyecto_id}/actividades", response_model=list[ActividadPublic])
def listar_actividades(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> list[ActividadPublic]:
    if session.get(Proyecto, proyecto_id) is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    get_accepted_participation(session, proyecto_id, usuario.id)
    actividades = session.exec(select(Actividad).where(Actividad.proyecto_id == proyecto_id)).all()
    return [ActividadPublic.from_model(actividad) for actividad in actividades]
