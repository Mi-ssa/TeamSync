from fastapi.testclient import TestClient

from test_iteracion1 import client, login, register, test_engine  # noqa: F401 (fixtures)


def equipo(client: TestClient, *nombres: str) -> tuple[int, list[dict], list[dict]]:
    """Crea un proyecto cuyo líder es el primer nombre; los demás aceptan la invitación."""
    usuarios = [register(client, nombre, f"{nombre.lower()}@example.com") for nombre in nombres]
    headers = [login(client, u["correo"]) for u in usuarios]
    proyecto_id = client.post("/proyectos", json={"nombre": "Proyecto"}, headers=headers[0]).json()["id"]
    for usuario, cabecera in zip(usuarios[1:], headers[1:]):
        invitacion = client.post(
            f"/proyectos/{proyecto_id}/invitaciones", json={"correo": usuario["correo"]}, headers=headers[0]
        ).json()
        client.post(f"/invitaciones/{invitacion['id']}/responder", json={"respuesta": "aceptar"}, headers=cabecera)
    return proyecto_id, usuarios, headers


def actividad(client, proyecto_id, headers, responsable_id, puntos, nombre="Tarea") -> int:
    respuesta = client.post(
        f"/proyectos/{proyecto_id}/actividades",
        json={"nombre": nombre, "puntos_acordados": puntos, "responsable_id": responsable_id},
        headers=headers,
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def votar_todos(client, actividad_id, headers, puntos):
    for cabecera in headers[1:]:
        client.post(f"/actividades/{actividad_id}/votos", json={"puntos": puntos}, headers=cabecera)


def completar(client, actividad_id, autor_headers, revisor_headers):
    avance = client.post(
        f"/actividades/{actividad_id}/avances", json={"descripcion": "Listo"}, headers=autor_headers
    )
    assert avance.status_code == 201, avance.text
    revision = client.patch(
        f"/avances/{avance.json()['id']}/revisar", json={"estado": "aprobado"}, headers=revisor_headers
    )
    assert revision.status_code == 200, revision.text


def evaluar(client, proyecto_id, headers, evaluado_id, confirma=True):
    respuesta = client.post(
        f"/proyectos/{proyecto_id}/evaluaciones",
        json={
            "evaluado_id": evaluado_id,
            "comunicacion": 5,
            "calidad": 4,
            "compromiso": 5,
            "confirma_aporte": confirma,
            "comentario": "Buen trabajo",
        },
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_puntos_se_acuerdan_por_votacion(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana", "Beto")
    act = actividad(client, proyecto_id, headers[0], usuarios[1]["id"], 6)

    listado = client.get(f"/proyectos/{proyecto_id}/actividades", headers=headers[1]).json()[0]
    assert listado["estado"] == "votacion"
    assert listado["votos_emitidos"] == 1 and listado["votos_requeridos"] == 3
    assert listado["mi_voto"] is None

    # No se trabaja hasta acordar los puntos.
    bloqueado = client.post(f"/actividades/{act}/avances", json={"descripcion": "x"}, headers=headers[1])
    assert bloqueado.status_code == 409

    # El líder no puede cerrar la votación sin mayoría (1 de 3).
    assert client.post(f"/actividades/{act}/cerrar-votacion", headers=headers[0]).status_code == 409
    voto = client.post(f"/actividades/{act}/votos", json={"puntos": 3}, headers=headers[1])
    assert voto.json()["estado"] == "votacion" and voto.json()["mi_voto"] == 3
    # Un integrante no puede cerrar la votación.
    assert client.post(f"/actividades/{act}/cerrar-votacion", headers=headers[1]).status_code == 403
    cerrada = client.post(f"/actividades/{act}/cerrar-votacion", headers=headers[0])
    assert cerrada.status_code == 200
    assert cerrada.json()["estado"] == "pendiente"
    assert cerrada.json()["puntos_acordados"] == 4.5  # mediana de 6 y 3

    # Si votan todos, se acuerda sola con la mediana.
    otra = actividad(client, proyecto_id, headers[0], usuarios[2]["id"], 2)
    client.post(f"/actividades/{otra}/votos", json={"puntos": 4}, headers=headers[1])
    final = client.post(f"/actividades/{otra}/votos", json={"puntos": 8}, headers=headers[2]).json()
    assert final["estado"] == "pendiente" and final["puntos_acordados"] == 4


def test_lider_no_aprueba_su_propio_avance_y_validaciones(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana", "Beto")
    propia = actividad(client, proyecto_id, headers[0], usuarios[0]["id"], 3)
    votar_todos(client, propia, headers, 3)
    avance = client.post(f"/actividades/{propia}/avances", json={"descripcion": "Hecho"}, headers=headers[0]).json()

    # Solo un avance pendiente a la vez.
    otro = client.post(f"/actividades/{propia}/avances", json={"descripcion": "Otro"}, headers=headers[0])
    assert otro.status_code == 409

    auto = client.patch(f"/avances/{avance['id']}/revisar", json={"estado": "aprobado"}, headers=headers[0])
    assert auto.status_code == 403
    por_par = client.patch(f"/avances/{avance['id']}/revisar", json={"estado": "aprobado"}, headers=headers[1])
    assert por_par.status_code == 200

    # Ya completada: no acepta más avances.
    tarde = client.post(f"/actividades/{propia}/avances", json={"descripcion": "Más"}, headers=headers[0])
    assert tarde.status_code == 409

    # Un integrante no revisa avances de otro integrante.
    de_ana = actividad(client, proyecto_id, headers[0], usuarios[1]["id"], 2)
    votar_todos(client, de_ana, headers, 2)
    avance_ana = client.post(f"/actividades/{de_ana}/avances", json={"descripcion": "Hecho"}, headers=headers[1]).json()
    beto = client.patch(f"/avances/{avance_ana['id']}/revisar", json={"estado": "aprobado"}, headers=headers[2])
    assert beto.status_code == 403


def test_contribucion_check_in_cierre_y_firma(client: TestClient):
    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana")
    lider, ana = usuarios
    a1 = actividad(client, proyecto_id, headers[0], lider["id"], 4, "Del líder")
    a2 = actividad(client, proyecto_id, headers[0], ana["id"], 4, "De Ana")
    votar_todos(client, a1, headers, 4)
    votar_todos(client, a2, headers, 4)

    # Sin trabajo aprobado no hay nada que validar: el check-in sigue cerrado.
    vacio = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[0]).json()
    assert vacio["checkin_abierto"] is False
    assert vacio["pendientes_cierre"][0] == "Todavía no hay actividades aprobadas en esta fase"
    temprano = client.post(
        f"/proyectos/{proyecto_id}/evaluaciones",
        json={"evaluado_id": ana["id"], "comunicacion": 3, "calidad": 3, "compromiso": 3},
        headers=headers[0],
    )
    assert temprano.status_code == 409

    completar(client, a1, headers[0], headers[1])
    completar(client, a2, headers[1], headers[0])

    contribucion = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[0]).json()
    assert contribucion["checkin_abierto"] is True
    assert contribucion["parte_justa"] == 4
    assert all(f["puntos_aprobados"] == 4 and f["puntos_validados"] == 0 for f in contribucion["integrantes"])
    assert not contribucion["puede_cerrar"]
    # Antes del check-in no se puede cerrar la fase.
    assert client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[0]).status_code == 409

    # El integrante ve solo su fila y un aviso privado.
    propia = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[1]).json()
    assert [f["usuario_id"] for f in propia["integrantes"]] == [ana["id"]]
    assert propia["aviso"].startswith("Aviso privado")
    assert propia["pendientes_cierre"] == []

    assert client.post(
        f"/proyectos/{proyecto_id}/evaluaciones",
        json={"evaluado_id": ana["id"], "comunicacion": 3, "calidad": 3, "compromiso": 3},
        headers=headers[1],
    ).status_code == 400  # no se autoevalúa
    evaluar(client, proyecto_id, headers[0], ana["id"])
    evaluar(client, proyecto_id, headers[1], lider["id"])

    contribucion = client.get(f"/proyectos/{proyecto_id}/contribucion", headers=headers[0]).json()
    assert all(f["porcentaje"] == 100 and f["cumple"] for f in contribucion["integrantes"])
    assert contribucion["integrantes"][0]["promedio_evaluacion"] == 4.67
    assert contribucion["puede_cerrar"]
    # Solo el líder cierra la fase.
    assert client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[1]).status_code == 403
    cerrada = client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[0])
    assert cerrada.status_code == 200 and cerrada.json()["fase_actual"] == 2

    # Antes de concluir no se firma.
    assert client.post(f"/proyectos/{proyecto_id}/declaracion/firmar", headers=headers[1]).status_code == 409
    concluido = client.post(f"/proyectos/{proyecto_id}/concluir", headers=headers[0])
    assert concluido.status_code == 200 and concluido.json()["estado"] == "concluido"
    assert client.post(f"/proyectos/{proyecto_id}/actividades", json={
        "nombre": "Tarde", "puntos_acordados": 1, "responsable_id": ana["id"]}, headers=headers[0]).status_code == 409

    declaracion = client.get(f"/proyectos/{proyecto_id}/declaracion", headers=headers[1]).json()
    assert declaracion["puntos_totales"] == 8 and declaracion["puedo_firmar"]
    firmada = client.post(f"/proyectos/{proyecto_id}/declaracion/firmar", headers=headers[1])
    assert firmada.status_code == 200
    fila_ana = next(f for f in firmada.json()["integrantes"] if f["usuario_id"] == ana["id"])
    assert fila_ana["firmado"] and fila_ana["porcentaje"] == 50 and fila_ana["actividades"] == ["De Ana"]
    assert client.post(f"/proyectos/{proyecto_id}/declaracion/firmar", headers=headers[1]).status_code == 409


def test_sin_aporte_validado_no_hay_firma_y_admin(client: TestClient):
    register(client, "Admin", "admin@teamsync.local")
    admin = login(client, "admin@teamsync.local")
    assert client.get("/auth/me", headers=admin).json()["es_admin"] is True

    proyecto_id, usuarios, headers = equipo(client, "Lider", "Ana", "Beto")
    lider, ana, beto = usuarios
    assert client.get("/admin/usuarios", headers=headers[0]).status_code == 403

    # Con el mínimo por defecto (70 %) Beto, que no aportó, bloquea el cierre.
    a1 = actividad(client, proyecto_id, headers[0], ana["id"], 6)
    votar_todos(client, a1, headers, 6)
    completar(client, a1, headers[1], headers[0])
    for evaluador in range(3):
        for evaluado in usuarios:
            if evaluado["id"] != usuarios[evaluador]["id"]:
                evaluar(client, proyecto_id, headers[evaluador], evaluado["id"], confirma=evaluado["id"] == ana["id"])
    bloqueo = client.post(f"/proyectos/{proyecto_id}/cerrar-fase", headers=headers[0])
    assert bloqueo.status_code == 409 and "Beto" in bloqueo.json()["detail"]

    reporte = client.get("/admin/reportes", headers=admin).json()
    assert reporte["proyectos"] == 1 and reporte["detalle"][0]["integrantes_bajo_minimo"] == 2

    # El administrador baja el mínimo a 0 %: la fase ya se puede cerrar.
    config = client.put("/admin/configuracion", json={"porcentaje_minimo": 0, "dias_inactividad": 3}, headers=admin)
    assert config.status_code == 200 and config.json()["porcentaje_minimo"] == 0
    assert client.post(f"/proyectos/{proyecto_id}/concluir", headers=headers[0]).status_code == 200

    sin_aporte = client.post(f"/proyectos/{proyecto_id}/declaracion/firmar", headers=headers[2])
    assert sin_aporte.status_code == 403
    assert sin_aporte.json()["detail"] == "Sin aporte validado no hay firma"
    assert client.get(f"/proyectos/{proyecto_id}/declaracion", headers=headers[2]).json()["puedo_firmar"] is False
    assert client.post(f"/proyectos/{proyecto_id}/declaracion/firmar", headers=headers[1]).status_code == 200

    # Gestión de usuarios: desactivar impide entrar.
    respuesta = client.patch(f"/admin/usuarios/{beto['id']}", json={"activo": False}, headers=admin)
    assert respuesta.status_code == 200 and respuesta.json()["activo"] is False
    assert client.post("/auth/login", json={"correo": beto["correo"], "contrasena": "contrasena-segura"}).status_code == 403
    assert client.get("/auth/me", headers=headers[2]).status_code == 401
    admin_id = client.get("/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/admin/usuarios/{admin_id}", json={"activo": False}, headers=admin).status_code == 400
    assert len(client.get("/admin/usuarios", headers=admin).json()) == 4
