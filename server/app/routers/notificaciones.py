from datetime import timezone

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.auth import CurrentUser, SessionDep
from app.models import Notificacion
from app.notificaciones import generar_recordatorios
from app.schemas import NotificacionesResponse, NotificacionPublic


router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


def _public(notificacion: Notificacion) -> NotificacionPublic:
    return NotificacionPublic(
        id=notificacion.id,
        tipo=notificacion.tipo,
        titulo=notificacion.titulo,
        mensaje=notificacion.mensaje,
        enlace=notificacion.enlace,
        leida=notificacion.leida,
        # SQLite devuelve fechas sin zona: se guardan en UTC, así que se marcan como UTC.
        creado_en=(
            notificacion.creado_en
            if notificacion.creado_en.tzinfo
            else notificacion.creado_en.replace(tzinfo=timezone.utc)
        ).isoformat(),
    )


def _respuesta(session: SessionDep, usuario_id: int) -> NotificacionesResponse:
    notificaciones = session.exec(
        select(Notificacion)
        .where(Notificacion.usuario_id == usuario_id)
        .order_by(Notificacion.id.desc())
        .limit(30)
    ).all()
    no_leidas = session.exec(
        select(func.count())
        .select_from(Notificacion)
        .where(Notificacion.usuario_id == usuario_id, Notificacion.leida == False)  # noqa: E712
    ).one()
    return NotificacionesResponse(no_leidas=no_leidas, notificaciones=[_public(n) for n in notificaciones])


@router.get("", response_model=NotificacionesResponse)
def mis_notificaciones(usuario: CurrentUser, session: SessionDep) -> NotificacionesResponse:
    generar_recordatorios(session, usuario.id)
    session.commit()
    return _respuesta(session, usuario.id)


@router.post("/leer-todas", response_model=NotificacionesResponse)
def marcar_todas(usuario: CurrentUser, session: SessionDep) -> NotificacionesResponse:
    for notificacion in session.exec(
        select(Notificacion).where(
            Notificacion.usuario_id == usuario.id, Notificacion.leida == False  # noqa: E712
        )
    ).all():
        notificacion.leida = True
        session.add(notificacion)
    session.commit()
    return _respuesta(session, usuario.id)


@router.post("/{notificacion_id}/leer", response_model=NotificacionPublic)
def marcar_leida(notificacion_id: int, usuario: CurrentUser, session: SessionDep) -> NotificacionPublic:
    notificacion = session.get(Notificacion, notificacion_id)
    if notificacion is None or notificacion.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notificacion.leida = True
    session.add(notificacion)
    session.commit()
    session.refresh(notificacion)
    return _public(notificacion)
