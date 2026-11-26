"""Notificaciones dentro de la app.

- Los eventos (invitaciones, votos, revisiones...) se crean en el momento en que
  ocurren, desde los routers, con `notificar`.
- Los recordatorios ("no olvides enviar tu avance", "no olvides calificar a tus
  compañeros") se generan al consultar las notificaciones, como máximo uno al día
  por proyecto, gracias a la `clave`, que incluye la fecha.
"""

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import Actividad, Avance, EvaluacionPares, Notificacion, Participacion, Proyecto


def notificar(
    session: Session,
    usuario_id: int,
    tipo: str,
    titulo: str,
    mensaje: str,
    enlace: str = "/dashboard",
    clave: str | None = None,
) -> None:
    if clave is not None:
        existente = session.exec(
            select(Notificacion).where(Notificacion.usuario_id == usuario_id, Notificacion.clave == clave)
        ).first()
        if existente is not None:
            return
    session.add(
        Notificacion(
            usuario_id=usuario_id, tipo=tipo, titulo=titulo, mensaje=mensaje, enlace=enlace, clave=clave
        )
    )


def notificar_varios(
    session: Session, usuarios: list[int], tipo: str, titulo: str, mensaje: str, enlace: str = "/dashboard"
) -> None:
    for usuario_id in usuarios:
        notificar(session, usuario_id, tipo, titulo, mensaje, enlace)


def enlace_proyecto(proyecto_id: int, vista: str | None = None) -> str:
    return f"/proyectos/{proyecto_id}" + (f"?vista={vista}" if vista else "")


def ids_miembros(session: Session, proyecto_id: int, excepto: int | None = None) -> list[int]:
    return [
        p.usuario_id
        for p in session.exec(
            select(Participacion).where(
                Participacion.proyecto_id == proyecto_id, Participacion.estado == "aceptada"
            )
        ).all()
        if p.usuario_id != excepto
    ]


def generar_recordatorios(session: Session, usuario_id: int) -> None:
    """Crea los recordatorios del día que apliquen a la persona."""
    hoy = datetime.now(timezone.utc).date().isoformat()
    participaciones = session.exec(
        select(Participacion).where(
            Participacion.usuario_id == usuario_id, Participacion.estado == "aceptada"
        )
    ).all()
    for participacion in participaciones:
        proyecto = session.get(Proyecto, participacion.proyecto_id)
        if proyecto is None or proyecto.estado != "activo":
            continue
        actividades = session.exec(
            select(Actividad).where(
                Actividad.proyecto_id == proyecto.id, Actividad.fase == proyecto.fase_actual
            )
        ).all()

        # 1) Actividades propias que todavía no tienen un avance enviado
        sin_avance = []
        for actividad in actividades:
            if actividad.responsable_id != usuario_id or actividad.estado != "pendiente":
                continue
            pendiente = session.exec(
                select(Avance).where(Avance.actividad_id == actividad.id, Avance.estado == "pendiente")
            ).first()
            if pendiente is None:
                sin_avance.append(actividad.nombre)
        if sin_avance:
            cuantas = len(sin_avance)
            lista = ", ".join(sin_avance[:3]) + ("…" if cuantas > 3 else "")
            notificar(
                session,
                usuario_id,
                "recordatorio",
                "No olvides enviar tu avance",
                f"Tienes {cuantas} actividad{'es' if cuantas != 1 else ''} sin avance en «{proyecto.nombre}»: {lista}.",
                enlace_proyecto(proyecto.id, "actividades"),
                clave=f"recordatorio-avance-{proyecto.id}-{hoy}",
            )

        # 2) Check-in abierto con compañeros sin calificar
        if not any(a.estado == "completada" for a in actividades):
            continue
        companeros = set(ids_miembros(session, proyecto.id, excepto=usuario_id))
        evaluados = {
            e.evaluado_id
            for e in session.exec(
                select(EvaluacionPares).where(
                    EvaluacionPares.proyecto_id == proyecto.id,
                    EvaluacionPares.fase == proyecto.fase_actual,
                    EvaluacionPares.evaluador_id == usuario_id,
                )
            ).all()
        }
        faltan = len(companeros - evaluados)
        if faltan:
            notificar(
                session,
                usuario_id,
                "recordatorio",
                "No olvides calificar a tus compañeros",
                (
                    f"Te falta evaluar a {faltan} compañero{'s' if faltan != 1 else ''} en el check-in "
                    f"de la fase {proyecto.fase_actual} de «{proyecto.nombre}»."
                ),
                enlace_proyecto(proyecto.id, "contribuciones"),
                clave=f"recordatorio-checkin-{proyecto.id}-{proyecto.fase_actual}-{hoy}",
            )
