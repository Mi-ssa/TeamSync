from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth import CurrentUser, SessionDep
from app.models import Actividad, Avance, Participacion
from app.routers.proyectos import get_accepted_participation
from app.schemas import AvanceCreate, AvanceDecision, AvancePublic


router = APIRouter(tags=["Actividades y avances"])


@router.post(
    "/actividades/{actividad_id}/avances",
    response_model=AvancePublic,
    status_code=status.HTTP_201_CREATED,
)
def registrar_avance(
    actividad_id: int, payload: AvanceCreate, usuario: CurrentUser, session: SessionDep
) -> AvancePublic:
    actividad = session.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    if actividad.responsable_id != usuario.id:
        raise HTTPException(status_code=403, detail="Solo el responsable puede registrar avances")
    avance = Avance(
        actividad_id=actividad_id,
        usuario_id=usuario.id,
        descripcion=payload.descripcion.strip(),
        url_evidencia=payload.url_evidencia,
    )
    session.add(avance)
    session.commit()
    session.refresh(avance)
    return AvancePublic.from_model(avance)


@router.get("/actividades/{actividad_id}/avances", response_model=list[AvancePublic])
def listar_avances(actividad_id: int, usuario: CurrentUser, session: SessionDep) -> list[AvancePublic]:
    actividad = session.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    avances = session.exec(select(Avance).where(Avance.actividad_id == actividad_id)).all()
    return [AvancePublic.from_model(avance) for avance in avances]


@router.patch("/avances/{avance_id}/revisar", response_model=AvancePublic)
def revisar_avance(
    avance_id: int, payload: AvanceDecision, usuario: CurrentUser, session: SessionDep
) -> AvancePublic:
    avance = session.get(Avance, avance_id)
    if avance is None:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    actividad = session.get(Actividad, avance.actividad_id)
    if actividad is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    participacion = get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    if participacion.rol != "lider":
        raise HTTPException(status_code=403, detail="Solo el líder puede revisar avances")
    if avance.estado != "pendiente":
        raise HTTPException(status_code=409, detail="El avance ya fue revisado")

    comentario = (payload.comentario or "").strip() or None
    if payload.estado == "rechazado" and comentario is None:
        raise HTTPException(status_code=400, detail="Escribe un comentario para explicar el rechazo")

    avance.estado = payload.estado
    avance.comentario_revision = comentario
    avance.revisado_en = datetime.now(timezone.utc)
    if payload.estado == "aprobado":
        actividad.estado = "completada"
    session.add(avance)
    session.add(actividad)
    session.commit()
    session.refresh(avance)
    return AvancePublic.from_model(avance)
