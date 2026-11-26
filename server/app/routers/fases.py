from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.auth import CurrentUser, SessionDep
from app.models import Actividad, Contribucion, EvaluacionPares, FirmaDeclaracion
from app.reglas import (
    cerrar_fase_actual,
    checkin_abierto,
    contribucion_response,
    evaluacion_public,
    exigir_proyecto_activo,
    get_proyecto,
    miembros_aceptados,
    nombre_usuario,
    puntos_validados_totales,
)
from app.notificaciones import enlace_proyecto, ids_miembros, notificar_varios
from app.routers.proyectos import get_accepted_participation
from app.schemas import (
    ContribucionResponse,
    DeclaracionIntegrante,
    DeclaracionResponse,
    EvaluacionCreate,
    EvaluacionPublic,
    ProyectoPublic,
    RetroalimentacionFase,
    RetroalimentacionResponse,
)


router = APIRouter(tags=["Contribuciones y cierre de fase"])


@router.get("/proyectos/{proyecto_id}/contribucion", response_model=ContribucionResponse)
def ver_contribucion(
    proyecto_id: int, usuario: CurrentUser, session: SessionDep, fase: int | None = None
) -> ContribucionResponse:
    proyecto = get_proyecto(session, proyecto_id)
    participacion = get_accepted_participation(session, proyecto_id, usuario.id)
    return contribucion_response(session, proyecto, usuario.id, participacion.rol, fase)


@router.post(
    "/proyectos/{proyecto_id}/evaluaciones",
    response_model=EvaluacionPublic,
    status_code=status.HTTP_201_CREATED,
)
def evaluar_par(
    proyecto_id: int, payload: EvaluacionCreate, usuario: CurrentUser, session: SessionDep
) -> EvaluacionPublic:
    """Check-in de la fase: cada integrante evalúa a cada compañero y confirma su aporte."""
    proyecto = get_proyecto(session, proyecto_id)
    get_accepted_participation(session, proyecto_id, usuario.id)
    exigir_proyecto_activo(proyecto)
    if not checkin_abierto(session, proyecto_id, proyecto.fase_actual):
        raise HTTPException(
            status_code=409,
            detail="El check-in se abre cuando hay al menos una actividad aprobada en la fase",
        )
    if payload.evaluado_id == usuario.id:
        raise HTTPException(status_code=400, detail="No puedes evaluarte a ti mismo")
    if payload.evaluado_id not in {m.usuario_id for m in miembros_aceptados(session, proyecto_id)}:
        raise HTTPException(status_code=400, detail="La persona evaluada no es integrante del proyecto")

    evaluacion = session.exec(
        select(EvaluacionPares).where(
            EvaluacionPares.proyecto_id == proyecto_id,
            EvaluacionPares.fase == proyecto.fase_actual,
            EvaluacionPares.evaluador_id == usuario.id,
            EvaluacionPares.evaluado_id == payload.evaluado_id,
        )
    ).first()
    if evaluacion is None:
        evaluacion = EvaluacionPares(
            proyecto_id=proyecto_id,
            fase=proyecto.fase_actual,
            evaluador_id=usuario.id,
            evaluado_id=payload.evaluado_id,
            puntuacion=0,
        )
    evaluacion.comunicacion = payload.comunicacion
    evaluacion.calidad = payload.calidad
    evaluacion.compromiso = payload.compromiso
    evaluacion.puntuacion = round((payload.comunicacion + payload.calidad + payload.compromiso) / 3, 2)
    evaluacion.confirma_aporte = payload.confirma_aporte
    evaluacion.comentario = (payload.comentario or "").strip() or None
    evaluacion.fortaleza = (payload.fortaleza or "").strip() or None
    evaluacion.mejora = (payload.mejora or "").strip() or None
    evaluacion.creado_en = datetime.now(timezone.utc)
    session.add(evaluacion)
    session.commit()
    session.refresh(evaluacion)
    return evaluacion_public(evaluacion)


def _solo_lider(session: SessionDep, proyecto_id: int, usuario_id: int) -> None:
    if get_accepted_participation(session, proyecto_id, usuario_id).rol != "lider":
        raise HTTPException(status_code=403, detail="Solo el líder puede hacer esta acción")


@router.post("/proyectos/{proyecto_id}/cerrar-fase", response_model=ProyectoPublic)
def cerrar_fase(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> ProyectoPublic:
    proyecto = get_proyecto(session, proyecto_id)
    _solo_lider(session, proyecto_id, usuario.id)
    exigir_proyecto_activo(proyecto)
    cerrar_fase_actual(session, proyecto)
    proyecto.fase_actual += 1
    session.add(proyecto)
    notificar_varios(
        session,
        ids_miembros(session, proyecto_id, excepto=usuario.id),
        "fase",
        f"Se cerró la fase {proyecto.fase_actual - 1} de «{proyecto.nombre}»",
        f"Ya trabajan en la fase {proyecto.fase_actual}.",
        enlace_proyecto(proyecto_id),
    )
    _avisar_retroalimentacion(session, proyecto, proyecto.fase_actual - 1)
    session.commit()
    session.refresh(proyecto)
    return ProyectoPublic.from_model(proyecto)


@router.post("/proyectos/{proyecto_id}/concluir", response_model=ProyectoPublic)
def concluir_proyecto(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> ProyectoPublic:
    proyecto = get_proyecto(session, proyecto_id)
    _solo_lider(session, proyecto_id, usuario.id)
    exigir_proyecto_activo(proyecto)
    actividades_fase = session.exec(
        select(Actividad).where(
            Actividad.proyecto_id == proyecto_id, Actividad.fase == proyecto.fase_actual
        )
    ).first()
    if actividades_fase is not None:
        # La fase en curso tiene trabajo: se cierra con las mismas reglas.
        cerrar_fase_actual(session, proyecto)
    session.flush()
    if not puntos_validados_totales(session, proyecto_id):
        session.rollback()
        raise HTTPException(status_code=409, detail="No hay aportes validados; cierra al menos una fase")
    proyecto.estado = "concluido"
    proyecto.concluido_en = datetime.now(timezone.utc)
    session.add(proyecto)
    if actividades_fase is not None:
        _avisar_retroalimentacion(session, proyecto, proyecto.fase_actual)
    con_aporte = puntos_validados_totales(session, proyecto_id)
    miembros = ids_miembros(session, proyecto_id)
    notificar_varios(
        session,
        [m for m in miembros if con_aporte.get(m, 0) > 0],
        "declaracion",
        f"Firma la declaración de «{proyecto.nombre}»",
        "El proyecto concluyó. Revisa tu contribución y firma la declaración.",
        enlace_proyecto(proyecto_id, "contribuciones"),
    )
    notificar_varios(
        session,
        [m for m in miembros if con_aporte.get(m, 0) <= 0],
        "declaracion",
        f"«{proyecto.nombre}» concluyó",
        "No tienes aporte validado, así que no puedes firmar la declaración.",
        enlace_proyecto(proyecto_id, "contribuciones"),
    )
    session.commit()
    session.refresh(proyecto)
    return ProyectoPublic.from_model(proyecto)


def _avisar_retroalimentacion(session: SessionDep, proyecto, fase: int) -> None:
    evaluados = {
        e.evaluado_id
        for e in session.exec(
            select(EvaluacionPares).where(
                EvaluacionPares.proyecto_id == proyecto.id, EvaluacionPares.fase == fase
            )
        ).all()
    }
    notificar_varios(
        session,
        [m for m in ids_miembros(session, proyecto.id) if m in evaluados],
        "retroalimentacion",
        f"Ya puedes ver tu retroalimentación de la fase {fase}",
        f"Tus compañeros te evaluaron en «{proyecto.nombre}». Los comentarios no llevan nombre.",
        enlace_proyecto(proyecto.id, "contribuciones"),
    )


def _promedio(valores: list[int]) -> float | None:
    return round(sum(valores) / len(valores), 2) if valores else None


@router.get("/proyectos/{proyecto_id}/mi-retroalimentacion", response_model=RetroalimentacionResponse)
def mi_retroalimentacion(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> RetroalimentacionResponse:
    """Promedios y comentarios que recibió la persona, solo de fases ya cerradas y sin
    decir quién escribió cada cosa (los comentarios se ordenan alfabéticamente)."""
    proyecto = get_proyecto(session, proyecto_id)
    get_accepted_participation(session, proyecto_id, usuario.id)
    ultima_cerrada = proyecto.fase_actual if proyecto.estado == "concluido" else proyecto.fase_actual - 1
    fases: list[RetroalimentacionFase] = []
    for fase in range(ultima_cerrada, 0, -1):
        recibidas = session.exec(
            select(EvaluacionPares).where(
                EvaluacionPares.proyecto_id == proyecto_id,
                EvaluacionPares.fase == fase,
                EvaluacionPares.evaluado_id == usuario.id,
            )
        ).all()
        if not recibidas:
            continue
        fases.append(
            RetroalimentacionFase(
                fase=fase,
                evaluaciones=len(recibidas),
                comunicacion=_promedio([e.comunicacion for e in recibidas]),
                calidad=_promedio([e.calidad for e in recibidas]),
                compromiso=_promedio([e.compromiso for e in recibidas]),
                promedio=round(
                    sum(e.comunicacion + e.calidad + e.compromiso for e in recibidas) / (3 * len(recibidas)), 2
                ),
                confirmaciones=sum(1 for e in recibidas if e.confirma_aporte),
                fortalezas=sorted(e.fortaleza for e in recibidas if e.fortaleza),
                mejoras=sorted(e.mejora for e in recibidas if e.mejora),
                comentarios=sorted(e.comentario for e in recibidas if e.comentario),
                anonima=len(recibidas) > 1,
            )
        )
    return RetroalimentacionResponse(
        fases=fases,
        fase_en_curso=proyecto.fase_actual if proyecto.estado == "activo" else None,
    )


def _declaracion(session: SessionDep, proyecto_id: int, usuario_id: int) -> DeclaracionResponse:
    proyecto = get_proyecto(session, proyecto_id)
    totales = puntos_validados_totales(session, proyecto_id)
    total = sum(totales.values())
    firmas = {
        f.usuario_id: f
        for f in session.exec(
            select(FirmaDeclaracion).where(FirmaDeclaracion.proyecto_id == proyecto_id)
        ).all()
    }
    integrantes: list[DeclaracionIntegrante] = []
    for miembro in miembros_aceptados(session, proyecto_id):
        actividades = session.exec(
            select(Actividad.nombre)
            .join(Contribucion, Contribucion.actividad_id == Actividad.id)
            .where(Actividad.proyecto_id == proyecto_id, Contribucion.usuario_id == miembro.usuario_id)
        ).all()
        puntos = totales.get(miembro.usuario_id, 0)
        firma = firmas.get(miembro.usuario_id)
        integrantes.append(
            DeclaracionIntegrante(
                usuario_id=miembro.usuario_id,
                nombre=nombre_usuario(session, miembro.usuario_id),
                rol=miembro.rol,
                puntos_validados=puntos,
                porcentaje=round(puntos / total * 100, 1) if total else 0,
                actividades=list(actividades),
                firmado=firma is not None,
                firmado_en=firma.creado_en.isoformat() if firma else None,
            )
        )
    motivo = None
    if proyecto.estado != "concluido":
        motivo = "La declaración se firma cuando el líder concluye el proyecto"
    elif totales.get(usuario_id, 0) <= 0:
        motivo = "Sin aporte validado no hay firma"
    elif usuario_id in firmas:
        motivo = "Ya firmaste la declaración"
    return DeclaracionResponse(
        proyecto_id=proyecto_id,
        nombre_proyecto=proyecto.nombre,
        concluido_en=proyecto.concluido_en.isoformat() if proyecto.concluido_en else None,
        puntos_totales=total,
        integrantes=integrantes,
        puedo_firmar=motivo is None,
        motivo=motivo,
    )


@router.get("/proyectos/{proyecto_id}/declaracion", response_model=DeclaracionResponse)
def ver_declaracion(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> DeclaracionResponse:
    get_proyecto(session, proyecto_id)
    get_accepted_participation(session, proyecto_id, usuario.id)
    return _declaracion(session, proyecto_id, usuario.id)


@router.post("/proyectos/{proyecto_id}/declaracion/firmar", response_model=DeclaracionResponse)
def firmar_declaracion(proyecto_id: int, usuario: CurrentUser, session: SessionDep) -> DeclaracionResponse:
    proyecto = get_proyecto(session, proyecto_id)
    get_accepted_participation(session, proyecto_id, usuario.id)
    if proyecto.estado != "concluido":
        raise HTTPException(status_code=409, detail="La declaración se firma cuando el líder concluye el proyecto")
    totales = puntos_validados_totales(session, proyecto_id)
    mis_puntos = totales.get(usuario.id, 0)
    if mis_puntos <= 0:
        raise HTTPException(status_code=403, detail="Sin aporte validado no hay firma")
    ya = session.exec(
        select(FirmaDeclaracion).where(
            FirmaDeclaracion.proyecto_id == proyecto_id, FirmaDeclaracion.usuario_id == usuario.id
        )
    ).first()
    if ya is not None:
        raise HTTPException(status_code=409, detail="Ya firmaste la declaración")
    total = sum(totales.values())
    session.add(
        FirmaDeclaracion(
            proyecto_id=proyecto_id,
            usuario_id=usuario.id,
            puntos_validados=mis_puntos,
            porcentaje=round(mis_puntos / total * 100, 1) if total else 0,
        )
    )
    session.commit()
    return _declaracion(session, proyecto_id, usuario.id)
