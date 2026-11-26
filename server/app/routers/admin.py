from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.auth import CurrentUser, SessionDep
from app.models import Actividad, Proyecto, Usuario
from app.reglas import (
    calcular_contribucion,
    get_config,
    integrantes_inactivos,
    miembros_aceptados,
    nombre_usuario,
    puntos_validados_totales,
)
from app.schemas import (
    ConfiguracionPublic,
    ConfiguracionUpdate,
    ReporteProyecto,
    ReporteResponse,
    UsuarioAdminUpdate,
    UsuarioPublic,
)


def require_admin(usuario: CurrentUser) -> Usuario:
    if not usuario.es_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador puede entrar aquí")
    return usuario


AdminUser = Annotated[Usuario, Depends(require_admin)]
router = APIRouter(prefix="/admin", tags=["Administración"])


@router.get("/usuarios", response_model=list[UsuarioPublic])
def listar_usuarios(_: AdminUser, session: SessionDep) -> list[Usuario]:
    return list(session.exec(select(Usuario).order_by(Usuario.id)).all())


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioPublic)
def actualizar_usuario(
    usuario_id: int, payload: UsuarioAdminUpdate, admin: AdminUser, session: SessionDep
) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.id == admin.id and (payload.activo is False or payload.es_admin is False):
        raise HTTPException(status_code=400, detail="No puedes desactivarte ni quitarte el rol a ti mismo")
    if payload.activo is not None:
        usuario.activo = payload.activo
    if payload.es_admin is not None:
        usuario.es_admin = payload.es_admin
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


@router.get("/configuracion", response_model=ConfiguracionPublic)
def ver_configuracion(_: AdminUser, session: SessionDep) -> ConfiguracionPublic:
    config = get_config(session)
    return ConfiguracionPublic(porcentaje_minimo=config.porcentaje_minimo, dias_inactividad=config.dias_inactividad)


@router.put("/configuracion", response_model=ConfiguracionPublic)
def actualizar_configuracion(
    payload: ConfiguracionUpdate, _: AdminUser, session: SessionDep
) -> ConfiguracionPublic:
    config = get_config(session)
    config.porcentaje_minimo = payload.porcentaje_minimo
    config.dias_inactividad = payload.dias_inactividad
    config.actualizado_en = datetime.now(timezone.utc)
    session.add(config)
    session.commit()
    return ConfiguracionPublic(porcentaje_minimo=config.porcentaje_minimo, dias_inactividad=config.dias_inactividad)


@router.get("/reportes", response_model=ReporteResponse)
def reportes(_: AdminUser, session: SessionDep) -> ReporteResponse:
    config = get_config(session)
    usuarios = session.exec(select(Usuario)).all()
    proyectos = session.exec(select(Proyecto).order_by(Proyecto.id)).all()
    detalle: list[ReporteProyecto] = []
    for proyecto in proyectos:
        actividades = session.exec(select(Actividad).where(Actividad.proyecto_id == proyecto.id)).all()
        bajo_minimo = 0
        if proyecto.estado == "activo":
            puntos_fase, _, _, filas, _ = calcular_contribucion(session, proyecto, proyecto.fase_actual)
            if puntos_fase > 0:
                bajo_minimo = sum(1 for fila in filas if not fila.cumple)
        detalle.append(
            ReporteProyecto(
                id=proyecto.id,
                nombre=proyecto.nombre,
                lider=nombre_usuario(session, proyecto.creado_por_id),
                estado=proyecto.estado,
                fase_actual=proyecto.fase_actual,
                integrantes=len(miembros_aceptados(session, proyecto.id)),
                actividades=len(actividades),
                actividades_completadas=sum(1 for a in actividades if a.estado == "completada"),
                puntos_totales=sum(a.puntos_acordados for a in actividades if a.estado != "votacion"),
                puntos_validados=sum(puntos_validados_totales(session, proyecto.id).values()),
                integrantes_bajo_minimo=bajo_minimo,
                integrantes_inactivos=integrantes_inactivos(session, proyecto, config.dias_inactividad),
            )
        )
    return ReporteResponse(
        usuarios=len(usuarios),
        usuarios_activos=sum(1 for u in usuarios if u.activo),
        proyectos=len(proyectos),
        proyectos_concluidos=sum(1 for p in proyectos if p.estado == "concluido"),
        porcentaje_minimo=config.porcentaje_minimo,
        dias_inactividad=config.dias_inactividad,
        detalle=detalle,
    )
