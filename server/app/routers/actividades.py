from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth import CurrentUser, SessionDep
from app.models import Actividad, Avance, Proyecto, VotoPuntos
from app.notificaciones import enlace_proyecto, ids_miembros, notificar, notificar_varios
from app.reglas import acordar_puntos, actividad_public, miembros_aceptados, votos_de
from app.routers.proyectos import get_accepted_participation
from app.schemas import ActividadPublic, AvanceCreate, AvanceDecision, AvancePublic, VotoCreate


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
    proyecto = session.get(Proyecto, actividad.proyecto_id)
    if proyecto is None or proyecto.estado != "activo":
        raise HTTPException(status_code=409, detail="El proyecto ya concluyó")
    if actividad.estado == "votacion":
        raise HTTPException(status_code=409, detail="El equipo todavía no acuerda los puntos de esta actividad")
    if actividad.estado == "completada":
        raise HTTPException(status_code=409, detail="La actividad ya está completada")
    if actividad.fase != proyecto.fase_actual:
        raise HTTPException(status_code=409, detail="La actividad no pertenece a la fase actual")
    pendiente = session.exec(
        select(Avance).where(Avance.actividad_id == actividad_id, Avance.estado == "pendiente")
    ).first()
    if pendiente is not None:
        raise HTTPException(status_code=409, detail="Ya tienes un avance esperando revisión en esta actividad")
    avance = Avance(
        actividad_id=actividad_id,
        usuario_id=usuario.id,
        descripcion=payload.descripcion.strip(),
        url_evidencia=payload.url_evidencia,
    )
    session.add(avance)
    # Revisa el líder; si el avance es del líder, lo puede revisar cualquier otro integrante.
    lider = next(m for m in miembros_aceptados(session, actividad.proyecto_id) if m.rol == "lider")
    revisores = (
        ids_miembros(session, actividad.proyecto_id, excepto=usuario.id)
        if usuario.id == lider.usuario_id
        else [lider.usuario_id]
    )
    notificar_varios(
        session,
        revisores,
        "revision",
        f"Revisa el avance de {usuario.nombre}",
        f"Envió un avance en «{actividad.nombre}» ({proyecto.nombre}).",
        enlace_proyecto(actividad.proyecto_id, "actividades"),
    )
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
    get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    if avance.usuario_id == usuario.id:
        raise HTTPException(
            status_code=403,
            detail="No puedes revisar tu propio avance; lo revisa otro integrante del equipo",
        )
    lider = next(m for m in miembros_aceptados(session, actividad.proyecto_id) if m.rol == "lider")
    # El líder revisa los avances del equipo; los avances del líder los revisa
    # cualquier otro integrante aceptado.
    if avance.usuario_id != lider.usuario_id and usuario.id != lider.usuario_id:
        raise HTTPException(status_code=403, detail="Solo el líder puede revisar avances")
    if avance.estado != "pendiente":
        raise HTTPException(status_code=409, detail="El avance ya fue revisado")

    comentario = (payload.comentario or "").strip() or None
    if payload.estado == "rechazado" and comentario is None:
        raise HTTPException(status_code=400, detail="Escribe un comentario para explicar el rechazo")

    avance.estado = payload.estado
    avance.comentario_revision = comentario
    avance.revisado_en = datetime.now(timezone.utc)
    checkin_ya_abierto = (
        session.exec(
            select(Actividad).where(
                Actividad.proyecto_id == actividad.proyecto_id,
                Actividad.fase == actividad.fase,
                Actividad.estado == "completada",
            )
        ).first()
        is not None
    )
    if payload.estado == "aprobado":
        actividad.estado = "completada"
    session.add(avance)
    session.add(actividad)
    enlace = enlace_proyecto(actividad.proyecto_id, "actividades")
    if payload.estado == "aprobado":
        notificar(session, avance.usuario_id, "resultado", f"Aprobaron tu avance en «{actividad.nombre}»",
                  f"{usuario.nombre} lo aprobó. Ya cuenta para tu contribución.", enlace)
    else:
        notificar(session, avance.usuario_id, "resultado", f"Rechazaron tu avance en «{actividad.nombre}»",
                  f"{usuario.nombre}: {comentario}", enlace)
    if payload.estado == "aprobado" and not checkin_ya_abierto:
        notificar_varios(
            session,
            ids_miembros(session, actividad.proyecto_id),
            "checkin",
            f"Ya puedes hacer tu check-in de la fase {actividad.fase}",
            "Hay trabajo aprobado: confirma el aporte de tus compañeros y califícalos.",
            enlace_proyecto(actividad.proyecto_id, "contribuciones"),
        )
    session.commit()
    session.refresh(avance)
    return AvancePublic.from_model(avance)


@router.post("/actividades/{actividad_id}/votos", response_model=ActividadPublic)
def votar_puntos(
    actividad_id: int, payload: VotoCreate, usuario: CurrentUser, session: SessionDep
) -> ActividadPublic:
    actividad = session.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    if actividad.estado != "votacion":
        raise HTTPException(status_code=409, detail="La votación de puntos ya cerró")
    voto = next((v for v in votos_de(session, actividad_id) if v.usuario_id == usuario.id), None)
    if voto is None:
        voto = VotoPuntos(actividad_id=actividad_id, usuario_id=usuario.id, puntos=payload.puntos)
    else:
        voto.puntos = payload.puntos
    session.add(voto)
    session.flush()
    if len(votos_de(session, actividad_id)) >= len(miembros_aceptados(session, actividad.proyecto_id)):
        acordar_puntos(session, actividad)
    session.commit()
    session.refresh(actividad)
    return actividad_public(session, actividad, usuario.id)


@router.post("/actividades/{actividad_id}/cerrar-votacion", response_model=ActividadPublic)
def cerrar_votacion(actividad_id: int, usuario: CurrentUser, session: SessionDep) -> ActividadPublic:
    actividad = session.get(Actividad, actividad_id)
    if actividad is None:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    participacion = get_accepted_participation(session, actividad.proyecto_id, usuario.id)
    if participacion.rol != "lider":
        raise HTTPException(status_code=403, detail="Solo el líder puede cerrar la votación")
    if actividad.estado != "votacion":
        raise HTTPException(status_code=409, detail="La votación de puntos ya cerró")
    emitidos = len(votos_de(session, actividad_id))
    miembros = len(miembros_aceptados(session, actividad.proyecto_id))
    if emitidos * 2 <= miembros:
        raise HTTPException(
            status_code=409,
            detail=f"Se necesita que vote la mayoría del equipo ({emitidos} de {miembros} votos)",
        )
    acordar_puntos(session, actividad)
    session.commit()
    session.refresh(actividad)
    return actividad_public(session, actividad, usuario.id)
