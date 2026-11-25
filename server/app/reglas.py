"""Reglas de negocio de la iteración 2: acuerdo de puntos, parte justa,
validación por pares, cierre de fase y declaración de contribución.

Definiciones (ver README):
- Parte justa de una fase = puntos acordados de la fase / integrantes activos.
- Puntos aprobados = puntos de las actividades del integrante que el revisor aprobó.
- Puntos validados = puntos aprobados que además confirmó la mayoría de sus pares
  en el check-in de la fase. Si el integrante trabaja solo, aprobados = validados.
- Cumplimiento = validados / parte justa * 100. Debe alcanzar el mínimo que fija
  el administrador (70 % por defecto) para poder cerrar la fase.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import (
    Actividad,
    Avance,
    Configuracion,
    Contribucion,
    EvaluacionPares,
    Participacion,
    Proyecto,
    Usuario,
    VotoPuntos,
)
from app.schemas import (
    ActividadPublic,
    ContribucionIntegrante,
    ContribucionResponse,
    EvaluacionPublic,
)


def get_config(session: Session) -> Configuracion:
    config = session.get(Configuracion, 1)
    if config is None:
        config = Configuracion(id=1)
        session.add(config)
        session.commit()
        session.refresh(config)
    return config


def miembros_aceptados(session: Session, proyecto_id: int) -> list[Participacion]:
    return list(
        session.exec(
            select(Participacion).where(
                Participacion.proyecto_id == proyecto_id,
                Participacion.estado == "aceptada",
            )
        ).all()
    )


def nombre_usuario(session: Session, usuario_id: int) -> str:
    usuario = session.get(Usuario, usuario_id)
    return usuario.nombre if usuario else "Integrante"


def get_proyecto(session: Session, proyecto_id: int) -> Proyecto:
    proyecto = session.get(Proyecto, proyecto_id)
    if proyecto is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto


def exigir_proyecto_activo(proyecto: Proyecto) -> None:
    if proyecto.estado != "activo":
        raise HTTPException(status_code=409, detail="El proyecto ya concluyó")


# --- Acuerdo de puntos (historia 3) ----------------------------------------


def votos_de(session: Session, actividad_id: int) -> list[VotoPuntos]:
    return list(session.exec(select(VotoPuntos).where(VotoPuntos.actividad_id == actividad_id)).all())


def actividad_public(session: Session, actividad: Actividad, usuario_id: int) -> ActividadPublic:
    votos = votos_de(session, actividad.id)
    mi_voto = next((voto.puntos for voto in votos if voto.usuario_id == usuario_id), None)
    return ActividadPublic.from_model(
        actividad,
        votos_emitidos=len(votos),
        votos_requeridos=len(miembros_aceptados(session, actividad.proyecto_id)),
        mi_voto=mi_voto,
    )


def acordar_puntos(session: Session, actividad: Actividad) -> None:
    """Fija los puntos con la mediana de los votos y abre la actividad."""
    votos = [voto.puntos for voto in votos_de(session, actividad.id)]
    if votos:
        actividad.puntos_acordados = round(float(median(votos)), 2)
    actividad.estado = "pendiente"
    session.add(actividad)


# --- Contribución y parte justa (historias 6 y 7) ---------------------------


def evaluaciones_fase(session: Session, proyecto_id: int, fase: int) -> list[EvaluacionPares]:
    return list(
        session.exec(
            select(EvaluacionPares).where(
                EvaluacionPares.proyecto_id == proyecto_id,
                EvaluacionPares.fase == fase,
            )
        ).all()
    )


def evaluacion_public(evaluacion: EvaluacionPares) -> EvaluacionPublic:
    return EvaluacionPublic(
        id=evaluacion.id,
        fase=evaluacion.fase,
        evaluador_id=evaluacion.evaluador_id,
        evaluado_id=evaluacion.evaluado_id,
        comunicacion=evaluacion.comunicacion,
        calidad=evaluacion.calidad,
        compromiso=evaluacion.compromiso,
        puntuacion=evaluacion.puntuacion,
        confirma_aporte=evaluacion.confirma_aporte,
        comentario=evaluacion.comentario,
    )


def calcular_contribucion(
    session: Session, proyecto: Proyecto, fase: int
) -> tuple[float, float, float, list[ContribucionIntegrante], list[str]]:
    """Devuelve (puntos_fase, parte_justa, minimo, filas, pendientes_cierre)."""
    minimo = get_config(session).porcentaje_minimo
    miembros = miembros_aceptados(session, proyecto.id)
    actividades = list(
        session.exec(
            select(Actividad).where(Actividad.proyecto_id == proyecto.id, Actividad.fase == fase)
        ).all()
    )
    puntos_fase = sum(a.puntos_acordados for a in actividades if a.estado != "votacion")
    parte_justa = puntos_fase / len(miembros) if miembros else 0
    evaluaciones = evaluaciones_fase(session, proyecto.id, fase)

    filas: list[ContribucionIntegrante] = []
    pendientes: list[str] = []
    for miembro in miembros:
        nombre = nombre_usuario(session, miembro.usuario_id)
        aprobados = sum(
            a.puntos_acordados
            for a in actividades
            if a.responsable_id == miembro.usuario_id and a.estado == "completada"
        )
        recibidas = [e for e in evaluaciones if e.evaluado_id == miembro.usuario_id]
        confirmaciones = sum(1 for e in recibidas if e.confirma_aporte)
        pares = len(miembros) - 1
        if pares == 0:
            validados = aprobados
        else:
            validados = aprobados if confirmaciones * 2 > pares else 0.0
        porcentaje = round(validados / parte_justa * 100, 1) if parte_justa > 0 else 100.0
        cumple = porcentaje >= minimo
        hechas = {e.evaluado_id for e in evaluaciones if e.evaluador_id == miembro.usuario_id}
        faltan = pares - len(hechas)
        promedio = (
            round(sum(e.puntuacion for e in recibidas) / len(recibidas), 2) if recibidas else None
        )
        filas.append(
            ContribucionIntegrante(
                usuario_id=miembro.usuario_id,
                nombre=nombre,
                rol=miembro.rol,
                puntos_aprobados=aprobados,
                puntos_validados=validados,
                porcentaje=porcentaje,
                cumple=cumple,
                confirmaciones=confirmaciones,
                evaluaciones_recibidas=len(recibidas),
                evaluaciones_pendientes=faltan,
                promedio_evaluacion=promedio,
            )
        )
        if faltan > 0:
            pendientes.append(f"{nombre} no ha terminado su check-in ({faltan} por evaluar)")
        if not cumple:
            pendientes.append(f"{nombre} tiene {porcentaje}% de su parte justa (mínimo {minimo:g}%)")
    if any(a.estado == "votacion" for a in actividades):
        pendientes.append("Hay actividades con la votación de puntos abierta")
    return puntos_fase, parte_justa, minimo, filas, pendientes


def contribucion_response(
    session: Session, proyecto: Proyecto, usuario_id: int, rol: str, fase: int | None = None
) -> ContribucionResponse:
    fase = fase or proyecto.fase_actual
    puntos_fase, parte_justa, minimo, filas, pendientes = calcular_contribucion(session, proyecto, fase)
    propia = next((f for f in filas if f.usuario_id == usuario_id), None)
    aviso = None
    if propia and not propia.cumple and puntos_fase > 0:
        aviso = (
            f"Aviso privado: tu aporte validado es {propia.porcentaje}% de tu parte justa "
            f"({parte_justa:g} pts). El mínimo para cerrar la fase es {minimo:g}%."
        )
    # El integrante ve su propia fila; el líder ve a todo el equipo para poder actuar.
    visibles = filas if rol == "lider" else [f for f in filas if f.usuario_id == usuario_id]
    mis = [
        evaluacion_public(e)
        for e in evaluaciones_fase(session, proyecto.id, fase)
        if e.evaluador_id == usuario_id
    ]
    return ContribucionResponse(
        fase=fase,
        estado_proyecto=proyecto.estado,
        porcentaje_minimo=minimo,
        puntos_fase=puntos_fase,
        parte_justa=round(parte_justa, 2),
        integrantes=visibles,
        mis_evaluaciones=mis,
        aviso=aviso,
        puede_cerrar=puntos_fase > 0 and not pendientes and proyecto.estado == "activo",
        pendientes_cierre=pendientes if rol == "lider" else [],
    )


def cerrar_fase_actual(session: Session, proyecto: Proyecto) -> None:
    """Valida las condiciones de cierre y guarda los puntos validados."""
    fase = proyecto.fase_actual
    puntos_fase, _, _, filas, pendientes = calcular_contribucion(session, proyecto, fase)
    if puntos_fase == 0:
        raise HTTPException(status_code=409, detail="La fase no tiene actividades con puntos acordados")
    if pendientes:
        raise HTTPException(status_code=409, detail="No se puede cerrar la fase: " + "; ".join(pendientes))
    validados = {f.usuario_id: f.puntos_validados > 0 for f in filas}
    actividades = session.exec(
        select(Actividad).where(Actividad.proyecto_id == proyecto.id, Actividad.fase == fase)
    ).all()
    for actividad in actividades:
        if actividad.estado == "completada":
            if validados.get(actividad.responsable_id):
                session.add(
                    Contribucion(
                        actividad_id=actividad.id,
                        usuario_id=actividad.responsable_id,
                        puntos_validados=actividad.puntos_acordados,
                    )
                )
        else:
            # Lo que no se terminó pasa a la siguiente fase.
            actividad.fase = fase + 1
            session.add(actividad)


def puntos_validados_totales(session: Session, proyecto_id: int) -> dict[int, float]:
    filas = session.exec(
        select(Contribucion, Actividad)
        .where(Contribucion.actividad_id == Actividad.id)
        .where(Actividad.proyecto_id == proyecto_id)
    ).all()
    totales: dict[int, float] = {}
    for contribucion, _ in filas:
        totales[contribucion.usuario_id] = totales.get(contribucion.usuario_id, 0) + contribucion.puntos_validados
    return totales


def integrantes_inactivos(session: Session, proyecto: Proyecto, dias: int) -> int:
    if proyecto.estado != "activo":
        return 0
    limite = datetime.now(timezone.utc) - timedelta(days=dias)
    inactivos = 0
    for miembro in miembros_aceptados(session, proyecto.id):
        ultimo = session.exec(
            select(Avance.creado_en)
            .join(Actividad, Avance.actividad_id == Actividad.id)
            .where(Actividad.proyecto_id == proyecto.id, Avance.usuario_id == miembro.usuario_id)
            .order_by(Avance.creado_en.desc())
        ).first()
        referencia = ultimo or miembro.respondido_en or miembro.creado_en
        if referencia.tzinfo is None:
            referencia = referencia.replace(tzinfo=timezone.utc)
        if referencia < limite:
            inactivos += 1
    return inactivos
